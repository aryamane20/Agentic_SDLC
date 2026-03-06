"""
PM Digital Twin — Schema Validator
Validates agent output against JSON schema + business rules.
"""

import json
from pathlib import Path
from jsonschema import validate, ValidationError, Draft7Validator


class SchemaValidator:
    """
    Validates PM Digital Twin output against output_schema.json
    plus business rules that can't be expressed in JSON schema.
    """

    def __init__(self, schema_path: str = None):
        if schema_path is None:
            schema_path = Path(__file__).parent.parent / "agent" / "schema" / "output_schema.json"
        else:
            schema_path = Path(schema_path)
        
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.validator = Draft7Validator(self.schema)

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
        
        # 1. JSON Schema validation
        validation_errors = list(self.validator.iter_errors(report))
        for error in validation_errors:
            errors.append(f"{'.'.join(str(p) for p in error.path)}: {error.message}")
        
        # 2. Business rules validation
        if not errors:  # Only check business rules if schema is valid
            warnings = self._check_business_rules(report)
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def _check_business_rules(self, report: dict) -> list:
        """
        Check business rules that can't be expressed in JSON schema.
        (Field normalization is done in validate() before this is called)
        """
        warnings = []
        
        # Phase rules
        phases = report.get("project_plan", {}).get("phases", [])
        if len(phases) != 5:
            warnings.append(f"Expected exactly 5 phases, found {len(phases)}")
        
        # Phase 1 must be >= 10%
        phase_1 = next((p for p in phases if p.get("phase_number") == 1), None)
        if phase_1 and phase_1.get("percentage_of_total", 0) < 10:
            warnings.append(f"Phase 1 is {phase_1.get('percentage_of_total')}%, must be >= 10%")
        
        # Phase 4 must be >= 15%
        phase_4 = next((p for p in phases if p.get("phase_number") == 4), None)
        if phase_4 and phase_4.get("percentage_of_total", 0) < 15:
            warnings.append(f"Phase 4 is {phase_4.get('percentage_of_total')}%, must be >= 15%")
        
        # Staffing: no role > 80%
        staffing = report.get("staffing_plan", [])
        for person in staffing:
            if person.get("allocation_percent", 0) > 80:
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
        
        return warnings

    def _normalize_field_names(self, report: dict):
        """
        Normalize field name variations from LLM output to match schema.
        
        Known variations:
        - classification -> project_type
        - assumptions -> assumption_log
        - risks -> risk_register
        - sdlc_methodology -> sdlc_approach
        """
        # Top-level field mappings
        field_mappings = {
            "classification": "project_type",
            "assumptions": "assumption_log",
            "risks": "risk_register",
            "sdlc_methodology": "sdlc_approach",
        }
        
        # Apply top-level mappings
        for old_name, new_name in field_mappings.items():
            if old_name in report and new_name not in report:
                report[new_name] = report.pop(old_name)
        
        # Handle report_metadata nested fields
        metadata = report.get("report_metadata", {})
        metadata_mappings = {
            "classification": "project_type",
            "sdlc_methodology": "sdlc_approach",
        }
        for old_name, new_name in metadata_mappings.items():
            if old_name in metadata and new_name not in metadata:
                metadata[new_name] = metadata.pop(old_name)
        
        # Set defaults if missing
        if "project_type" not in metadata:
            metadata["project_type"] = "UNKNOWN"
        if "sdlc_approach" not in metadata:
            metadata["sdlc_approach"] = "UNKNOWN"
        if "input_quality" not in metadata:
            metadata["input_quality"] = "UNKNOWN"
