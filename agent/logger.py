"""
PM Digital Twin — Structured Logger
Logs agent outputs in structured JSON format for analysis.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any


class PMReportLogger:
    """
    Structured logger for PM Digital Twin reports.
    Logs to both file (JSON) and console (human-readable summary).
    """

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure file logger
        self.file_handler = logging.FileHandler(
            self.log_dir / f"pm_agent_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
        )
        self.file_handler.setFormatter(logging.Formatter('%(message)s'))
        
        # Configure console logger
        self.console_handler = logging.StreamHandler()
        self.console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        
        # Root logger
        self.logger = logging.getLogger("PMDigitalTwin")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.file_handler)
        self.logger.addHandler(self.console_handler)

    def log_report(self, report: Dict[str, Any], metadata: Dict[str, Any] = None):
        """
        Log a complete PM report.
        
        Args:
            report: The parsed PM report dictionary
            metadata: Optional metadata (input source, runtime, etc.)
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "report_id": metadata.get("report_id") if metadata else None,
            "input_source": metadata.get("input_source") if metadata else None,
            "runtime_seconds": metadata.get("runtime_seconds") if metadata else None,
            "tokens_used": metadata.get("tokens_used") if metadata else None,
            "cache_read_tokens": metadata.get("cache_read_tokens") if metadata else 0,
            "cache_creation_tokens": metadata.get("cache_creation_tokens") if metadata else 0,
            "report": report,
            "summary": self._generate_summary(report)
        }
        
        # Log as JSON to file (default=str avoids rare non-serializable values e.g. in tests)
        self.logger.info(json.dumps(log_entry, default=str))
        
        # Log summary to console with cache status
        cache_read = metadata.get("cache_read_tokens", 0) if metadata else 0
        cache_created = metadata.get("cache_creation_tokens", 0) if metadata else 0
        cache_status = "cache_read" if cache_read > 0 else ("cache_created" if cache_created > 0 else "no_cache")
        self.logger.info(f"Report generated: {log_entry['summary']} | {cache_status}")
        
        return log_entry

    def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """
        Log an error that occurred during processing.
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context or {}
        }
        
        self.logger.error(json.dumps(log_entry, default=str))

    def _generate_summary(self, report: Dict[str, Any]) -> str:
        """
        Generate a human-readable summary of the report.
        """
        # Get key metrics
        metadata = report.get("report_metadata", {})
        score = report.get("pm_confidence_score", {})
        
        if isinstance(score, dict):
            score_val = score.get("score", "N/A")
        else:
            score_val = score
        
        project_type = metadata.get("project_type", "UNKNOWN")
        sdlc = metadata.get("sdlc_approach", "UNKNOWN")
        
        # Count items
        phases = len(report.get("project_plan", {}).get("phases", []))
        tasks = sum(len(p.get("tasks", [])) for p in report.get("project_plan", {}).get("phases", []))
        risks = len(report.get("risk_register", []))
        assumptions = len(report.get("assumption_log", []))
        
        return (
            f"Type: {project_type} | SDLC: {sdlc} | "
            f"Confidence: {score_val} | "
            f"Phases: {phases} | Tasks: {tasks} | Risks: {risks} | Assumptions: {assumptions}"
        )
