"""
PM Digital Twin — Schema Validator
Validates agent output using Pydantic models + business rules.
"""

import json
from pathlib import Path
from pydantic import ValidationError as PydanticValidationError
from schemas.output_schema import PMReport


def sync_pm_confidence_metadata_mirrors(report: dict) -> None:
    """
    Canonical numeric PM confidence is pm_confidence_score.score (top-level object).
    Mirror the same float into report_metadata.pm_confidence_score for parity with the prompt
    and gate logic.
    """
    pm_top = report.get("pm_confidence_score")
    if isinstance(pm_top, dict) and pm_top.get("score") is not None:
        try:
            canon = float(pm_top["score"])
            metadata = report.setdefault("report_metadata", {})
            metadata["pm_confidence_score"] = canon
        except (TypeError, ValueError):
            pass


class SchemaValidator:
    """
    Validates PM Digital Twin output using Pydantic models
    plus business rules that can't be expressed in schema.
    """

    def __init__(self, schema_path: str = None):
        pass  # No longer need schema path

    def validate(self, report: dict) -> dict:
        """
        Validate a report against schema + business rules.
        
        Returns:
            dict with:
                - valid: bool
                - errors: list of schema validation errors
                - warnings: list of business rule violations
        """
        # First normalize field names (flexible schema)
        self._normalize_field_names(report)
        
        errors = []
        warnings = []
        
        # 1. Pydantic validation
        try:
            validated = PMReport(**report)
        except PydanticValidationError as e:
            for error in e.errors():
                field = '.'.join(str(loc) for loc in error['loc'])
                errors.append(f"{field}: {error['msg']}")
        
        # 2. Business rules validation (only if schema valid)
        if not errors:
            br_errors, warnings = self._check_business_rules(report)
            errors.extend(br_errors)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def _check_business_rules(self, report: dict) -> tuple:
        """
        Check business rules that can't be expressed in JSON schema.
        Returns (errors, warnings) — errors cause D1 FAIL.
        """
        errors = []
        warnings = []
        
        # Phase rules
        phases = report.get("project_plan", {}).get("phases", [])
        if len(phases) != 5:
            warnings.append(f"Expected exactly 5 phases, found {len(phases)}")
        
        # Phase 1 must be >= 10%
        phase_1 = next((p for p in phases if p.get("phase_number") == 1), None)
        if phase_1 and phase_1.get("percentage_of_total", 0) < 10:
            warnings.append(f"Phase 1 is {phase_1.get('percentage_of_total')}%, must be >= 10%")
        
        # Phase 4 must be >= 15% — HARD MINIMUM (F3 pre-mortem)
        phase_4 = next((p for p in phases if p.get("phase_number") == 4), None)
        if phase_4 and phase_4.get("percentage_of_total", 0) < 15:
            errors.append(f"Phase 4 is {phase_4.get('percentage_of_total')}%, must be >= 15% — HARD MINIMUM")

        # Phase 5 band is 5-10% — ceiling 10% (architecture / prompt band)
        phase_5 = next((p for p in phases if p.get("phase_number") == 5), None)
        if phase_5 is not None:
            p5_pct = float(phase_5.get("percentage_of_total") or 0)
            if p5_pct > 10:
                warnings.append(
                    f"Phase 5 is {phase_5.get('percentage_of_total')}%, must be <= 10% "
                    "(Deployment & Handoff band maximum)"
                )
        
        # Staffing: no role > 80% (actionable plan hygiene).
        # Skip when already NOT_VIABLE — high allocation reflects impossible inputs, not agent error.
        viability_early = report.get("project_viability") or {}
        viability_status_early = (viability_early.get("viability_status") or "").strip()
        staffing = report.get("staffing_plan", [])
        for person in staffing:
            if viability_status_early != "NOT_VIABLE" and person.get("allocation_percent", 0) > 80:
                warnings.append(f"Role {person.get('role')} is allocated {person.get('allocation_percent')}%, exceeds 80%")
        
        # QA rule: QA hours >= 25% of dev hours
        # This would require calculating from tasks - skipping for now
        
        # Risk register: at least 3 risks
        risks = report.get("risk_register", [])
        if len(risks) < 3:
            warnings.append(f"Risk register has {len(risks)} risks, expected at least 3")
        
        # Assumption log: at least 1
        assumptions = report.get("assumption_log", [])
        if len(assumptions) < 1:
            warnings.append("Assumption log is empty, expected at least 1 assumption")
        
        # PM Confidence Score: 0-100
        score = report.get("pm_confidence_score", {})
        if isinstance(score, dict):
            score_val = score.get("score", 0)
        else:
            score_val = score
        
        if not (0 <= score_val <= 100):
            warnings.append(f"PM Confidence Score is {score_val}, must be 0-100")
        
        # Open questions: max 5
        open_questions = report.get("open_questions", [])
        if len(open_questions) > 5:
            warnings.append(f"Open questions: {len(open_questions)}, expected max 5")
        
        # Critical path: every task must have critical_path boolean
        all_tasks = []
        for phase in phases:
            all_tasks.extend(phase.get("tasks", []))
        
        tasks_without_critical_path = [t.get("name", "unnamed") for t in all_tasks if "critical_path" not in t]
        if tasks_without_critical_path:
            warnings.append(f"Tasks missing critical_path field: {tasks_without_critical_path}")
        
        # Slack days: every task must have slack_days integer
        tasks_without_slack = [t.get("name", "unnamed") for t in all_tasks if "slack_days" not in t]
        if tasks_without_slack:
            warnings.append(f"Tasks missing slack_days field: {tasks_without_slack}")
        
        # Hard cap enforcement — violations are errors, not warnings
        assumptions = report.get("assumption_log", [])
        assumption_count = len(assumptions)
        critical_risks = [r for r in risks if r.get("score") == "CRITICAL"]

        if assumption_count >= 8 and score_val > 40:
            errors.append(f"Hard cap violated: score {score_val} with {assumption_count} assumptions (>=8), max allowed 40")
        elif assumption_count >= 5 and score_val > 60:
            errors.append(f"Hard cap violated: score {score_val} with {assumption_count} assumptions (>=5), max allowed 60")

        if critical_risks and assumption_count >= 3 and score_val > 50:
            errors.append(f"Hard cap violated: score {score_val} with {len(critical_risks)} CRITICAL risk(s) and {assumption_count} assumptions (>=3), max allowed 50")
        
        # Viability section validation
        viability = report.get("project_viability")
        if viability:
            # If viability exists, it should have valid status
            status = viability.get("viability_status", "")
            if status not in ["VIABLE", "AT_RISK", "NOT_VIABLE", "CANNOT_ASSESS"]:
                warnings.append(f"Invalid viability_status: {status}")
            
            # If status is NOT_VIABLE, scoping_options should exist
            if status == "NOT_VIABLE":
                scoping = viability.get("scoping_options", [])
                if not scoping:
                    warnings.append("viability_status is NOT_VIABLE but no scoping_options provided")
                elif len(scoping) < 2:
                    warnings.append("viability_status is NOT_VIABLE but fewer than 2 scoping_options provided")
        
        return errors, warnings

    def _normalize_field_names(self, report: dict):
        """
        Normalize field name variations from LLM output to match schema.
        
        Known variations from LLM:
        - classification -> project_type (move to metadata)
        - assumptions -> assumption_log
        - risks -> risk_register
        - pm_confidence -> pm_confidence_score
        - viability -> project_viability
        """
        # Top-level field mappings
        field_mappings = {
            "assumptions": "assumption_log",
            "risks": "risk_register",
            "pm_confidence": "pm_confidence_score",
            "viability": "project_viability",
        }
        
        # Apply top-level mappings
        for old_name, new_name in field_mappings.items():
            if old_name in report and new_name not in report:
                report[new_name] = report.pop(old_name)
        
        # Handle classification - move to report_metadata
        if "classification" in report:
            classification = report.pop("classification")
            metadata = report.get("report_metadata", {})
            if "project_type" not in metadata and "project_type" in classification:
                metadata["project_type"] = classification.get("project_type")
            if "sdlc_approach" not in metadata and "sdlc_approach" in classification:
                metadata["sdlc_approach"] = classification.get("sdlc_approach")
            report["report_metadata"] = metadata
        
        # Handle report_metadata nested fields
        metadata = report.get("report_metadata", {})
        
        # Fix project_type - LLM outputs "TYPE A: ..." instead of "TYPE_A"
        if metadata.get("project_type"):
            pt = metadata["project_type"]
            if isinstance(pt, str):
                # Map LLM output to enum values
                if "TYPE A" in pt.upper():
                    metadata["project_type"] = "TYPE_A"
                elif "TYPE B" in pt.upper():
                    metadata["project_type"] = "TYPE_B"
                elif "TYPE C" in pt.upper():
                    metadata["project_type"] = "TYPE_C"
                elif "TYPE D" in pt.upper():
                    metadata["project_type"] = "TYPE_D"
                elif "TYPE E" in pt.upper():
                    metadata["project_type"] = "TYPE_E"
                elif "TYPE F" in pt.upper():
                    metadata["project_type"] = "TYPE_F"
        
        # Fix pm_confidence_score structure - LLM puts deductions inside breakdown
        pm_conf = report.get("pm_confidence_score")
        if pm_conf and "breakdown" in pm_conf:
            breakdown = pm_conf.pop("breakdown")
            if "deductions" in breakdown:
                pm_conf["deductions"] = breakdown["deductions"]
            if "starting_score" in breakdown:
                pm_conf["score"] = breakdown.get("starting_score", pm_conf.get("score"))
            if "interpretation" in breakdown:
                pm_conf["interpretation"] = breakdown["interpretation"]

        sync_pm_confidence_metadata_mirrors(report)
        
        # Set defaults if missing (use valid enum values)
        if "project_type" not in metadata or not metadata.get("project_type"):
            metadata["project_type"] = "TYPE_A"  # Default valid enum
        if "sdlc_approach" not in metadata or not metadata.get("sdlc_approach"):
            metadata["sdlc_approach"] = "Hybrid"  # Default valid enum
        if "input_quality" not in metadata or not metadata.get("input_quality"):
            metadata["input_quality"] = "MEDIUM"  # Default valid enum
