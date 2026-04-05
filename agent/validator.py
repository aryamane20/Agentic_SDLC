"""
PM Digital Twin — Schema Validator
Validates agent output using Pydantic models + business rules.
"""

import json
from pathlib import Path
from pydantic import ValidationError as PydanticValidationError
from schemas.output_schema import PMReport


def _role_lower(person: dict) -> str:
    return (person.get("role") or "").strip().lower()


def _staffing_hours(person: dict) -> float:
    try:
        return float(person.get("total_hours") or 0)
    except (TypeError, ValueError):
        return 0.0


def _is_qa_role(role_l: str) -> bool:
    if "backend developer" in role_l or "frontend developer" in role_l:
        return "qa" in role_l or "test" in role_l
    return any(
        t in role_l
        for t in (
            "qa engineer",
            "qa lead",
            "quality assurance",
            "quality engineer",
            "test engineer",
            "sdet",
            "software tester",
            "test analyst",
        )
    ) or role_l.startswith("qa ") or role_l in ("qa", "tester")


def _is_pm_role(role_l: str) -> bool:
    return any(
        x in role_l
        for x in (
            "project manager",
            "product manager",
            "product owner",
            "scrum master",
            "delivery manager",
            "program manager",
        )
    ) or role_l in ("pm", "po")


def _qa_and_dev_hours(staffing: list) -> tuple[float, float]:
    qa_h = 0.0
    dev_h = 0.0
    for p in staffing:
        rl = _role_lower(p)
        h = _staffing_hours(p)
        if _is_qa_role(rl):
            qa_h += h
        elif _is_pm_role(rl):
            continue
        else:
            dev_h += h
    return qa_h, dev_h


def _risk_blob(r: dict) -> str:
    parts = [r.get("description"), r.get("mitigation"), r.get("trigger")]
    return " ".join(str(p or "") for p in parts).lower()


def _is_qa_staffing_ratio_risk(r: dict) -> bool:
    """Risk row that explicitly covers QA hours vs the 25% implementation-effort rule."""
    t = _risk_blob(r)
    if not any(k in t for k in ("qa", "quality assurance", "test coverage", "testing ", "qa ")):
        return False
    return any(
        k in t
        for k in (
            "25%",
            "hour",
            "allocation",
            "staff",
            "underalloc",
            "under-alloc",
            "under alloc",
            "ratio",
            "effort",
            "compress",
            "compressed",
            "pmi",
            "minimum",
            "below ",
            "below minimum",
            "material",
        )
    )


def _best_qa_ratio_risk_score(risks: list) -> str | None:
    """Highest score among risks that look like QA staffing / 25% rule; None if none."""
    order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    best = None
    best_rank = 0
    for r in risks:
        if not _is_qa_staffing_ratio_risk(r):
            continue
        sc = (r.get("score") or "").strip().upper()
        rank = order.get(sc, 0)
        if rank > best_rank:
            best_rank = rank
            best = sc
    return best


def _project_understanding_blob(report: dict) -> str:
    pu = report.get("project_understanding") or {}
    parts: list[str] = []
    for key in ("primary_goal", "beneficiary", "trigger"):
        v = pu.get(key)
        if v:
            parts.append(str(v))
    sd = pu.get("success_definition")
    if isinstance(sd, list):
        parts.extend(str(x) for x in sd)
    elif sd:
        parts.append(str(sd))
    for q in pu.get("supporting_quotes") or []:
        parts.append(str(q))
    return " ".join(parts).lower()


def _expansion_classes_for_role(role_l: str) -> list[str]:
    classes: list[str] = []
    if _is_pm_role(role_l):
        classes.append("pm")
    if _is_qa_role(role_l):
        classes.append("qa")
    if any(
        k in role_l
        for k in ("ux designer", "ux ", " ux", "user experience", "ui designer")
    ):
        classes.append("ux")
    if any(k in role_l for k in ("security", "secops", "appsec")):
        classes.append("security")
    if any(k in role_l for k in ("devops", "sre", "platform eng", "site reliability")):
        classes.append("devops")
    return classes


def _brief_mentions_expansion_class(brief_blob: str, cls: str) -> bool:
    if cls == "pm":
        return any(
            k in brief_blob
            for k in (
                "project manager",
                "product manager",
                "product owner",
                "scrum master",
                "program manager",
                "delivery manager",
                "pm ",
                " pm",
            )
        )
    if cls == "qa":
        return any(
            k in brief_blob
            for k in (
                "qa ",
                " qa",
                "quality assurance",
                "test engineer",
                "sdet",
                "testing team",
                "q.e.",
            )
        )
    if cls == "ux":
        return any(
            k in brief_blob
            for k in (
                "ux",
                "designer",
                "ui ",
                "figma",
                "user research",
            )
        )
    if cls == "security":
        return any(k in brief_blob for k in ("security", "appsec", "secops"))
    if cls == "devops":
        return any(
            k in brief_blob
            for k in ("devops", "sre", "platform eng", "infrastructure", "ci/cd", "pipeline")
        )
    return True


def _assumptions_mention_class(assumption_blob: str, cls: str) -> bool:
    if cls == "pm":
        return any(
            k in assumption_blob
            for k in (
                "project manager",
                "product manager",
                "product owner",
                "scrum master",
                "program manager",
                "delivery manager",
                "pm allocation",
                " pm ",
            )
        )
    return _brief_mentions_expansion_class(assumption_blob, cls)


def _oq_is_formal_signoff_or_hr_execution_question(question: str) -> bool:
    t = (question or "").lower()
    keys = (
        "formally signed",
        "formal",
        "written",
        "sign-off",
        "sign off",
        "signed off",
        "signoff",
        "hr team",
        "hr lead",
        "stakeholder approval",
        "formally approve",
        "formal approval",
        "signed off on",
        "documentation of",
    )
    return any(k in t for k in keys)


def _assumption_claims_stakeholder_or_scope_approval_complete(assumptions: list) -> bool:
    """True when the log assumes approvals / alignment are already settled (Q4 vs A7 class)."""
    for a in assumptions or []:
        blob = (
            f"{a.get('what', '')} {a.get('why', '')} "
            f"{a.get('consequence', '')} {a.get('pmi_basis', '')}"
        ).lower()
        if "stakeholder" in blob and any(
            x in blob
            for x in (
                "assumed",
                "assumption",
                "complete",
                "achieved",
                "documented",
                "alignment",
                "signed off",
                "sign-off",
            )
        ):
            return True
        if "approval" in blob and "scope" in blob and any(
            x in blob for x in ("assumed", "complete", "documented", "alignment", "achieved")
        ):
            return True
        if ("sign-off" in blob or "sign off" in blob) and any(
            x in blob for x in ("assumed", "complete", "documented", "alignment", "achieved")
        ):
            return True
    return False


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

        # Phase 5 band is 5-10% — ceiling 10% (HARD; JSON 10.7% matches broken prompt compliance)
        phase_5 = next((p for p in phases if p.get("phase_number") == 5), None)
        if phase_5 is not None:
            p5_pct = float(phase_5.get("percentage_of_total") or 0)
            if p5_pct > 10:
                errors.append(
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
        
        # Risk register: at least 3 risks
        risks = report.get("risk_register", [])
        if len(risks) < 3:
            warnings.append(f"Risk register has {len(risks)} risks, expected at least 3")

        # QA total_hours >= 25% of implementation hours (excl. PM); else require HIGH/CRITICAL
        # ratio risk (under-allocation is factual when hours are short — not MEDIUM/LOW).
        qa_h, dev_h = _qa_and_dev_hours(staffing)
        if staffing and dev_h > 0 and qa_h + 1e-6 < 0.25 * dev_h:
            best = _best_qa_ratio_risk_score(risks)
            if best not in ("CRITICAL", "HIGH"):
                msg = (
                    f"QA total_hours ({qa_h:g}) is below 25% of implementation hours ({dev_h:g}) "
                    "— risk_register must include a CRITICAL or HIGH risk explicitly tied to "
                    "QA under-allocation vs the 25% rule (not MEDIUM/LOW; gap is certain)."
                )
                if best in ("LOW", "MEDIUM"):
                    msg += f" Found {best} severity on matching risk row(s)."
                errors.append(msg)
        
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
        
        # Open questions: max 5 + urgency vs plan consistency
        open_questions = report.get("open_questions", [])
        if len(open_questions) > 5:
            warnings.append(f"Open questions: {len(open_questions)}, expected max 5")
        has_before_planning = any(
            str(oq.get("urgency", "")).strip().lower() == "before planning"
            for oq in open_questions
        )
        task_count_plan = sum(len(p.get("tasks") or []) for p in phases)

        # Sign-off / HR documentation vs assumptions (Q4 class) — invalid Before planning
        if assumptions:
            for oq in open_questions:
                if str(oq.get("urgency", "")).strip().lower() != "before planning":
                    continue
                qtext = str(oq.get("question", ""))
                if _oq_is_formal_signoff_or_hr_execution_question(qtext):
                    if _assumption_claims_stakeholder_or_scope_approval_complete(assumptions):
                        errors.append(
                            "Open question uses 'Before planning' for formal written / HR / "
                            "sign-off confirmation while assumption_log already treats "
                            "stakeholder or scope approval as assumed or complete — "
                            "contradiction; use 'Before build'."
                        )
                        break

        if has_before_planning and len(phases) >= 5 and task_count_plan >= 1:
            errors.append(
                "Open question urgency 'Before planning' is inconsistent with a populated "
                "project_plan (phases and tasks) — decomposition already occurred; use "
                "'Before build' unless no tasks exist in any phase."
            )
        
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

        # Staffing expansion: QA/UX/Security/DevOps not reflected in brief proxy → assumption rows
        brief_blob = _project_understanding_blob(report)
        assumption_blob = " ".join(
            f"{a.get('what', '')} {a.get('why', '')} {a.get('consequence', '')}"
            for a in assumptions
        ).lower()
        warned_classes: set[str] = set()
        for person in staffing:
            role_l = _role_lower(person)
            for cls in _expansion_classes_for_role(role_l):
                if cls in warned_classes:
                    continue
                if _brief_mentions_expansion_class(brief_blob, cls):
                    continue
                if _assumptions_mention_class(assumption_blob, cls):
                    continue
                warnings.append(
                    f"Staffing adds expanded role class {cls.upper()} ({person.get('role')}) "
                    "not evidenced in project_understanding text — missing dedicated "
                    "assumption_log row per v1.6.2 staffing rule."
                )
                warned_classes.add(cls)

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
