"""
Log Analyzer for PM Digital Twin
Parses logs/runs/ for latency, failure rate, and other statistics.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from collections import defaultdict


def parse_log_file(log_path: Path) -> List[Dict[str, Any]]:
    """Parse a JSONL log file and return list of log entries."""
    entries = []
    with open(log_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def analyze_runs(log_dir: Path) -> Dict[str, Any]:
    """Analyze all run logs in the logs directory."""
    stats = {
        "total_runs": 0,
        "successful_runs": 0,
        "failed_runs": 0,
        "total_runtime_seconds": 0,
        "total_tokens": 0,
        "avg_runtime_seconds": 0,
        "avg_tokens": 0,
        "by_input_source": defaultdict(lambda: {"count": 0, "success": 0, "fail": 0}),
        "by_date": defaultdict(lambda: {"count": 0, "success": 0, "fail": 0}),
    }
    
    # Find all log files
    log_files = list(log_dir.glob("*.jsonl"))
    
    for log_file in log_files:
        entries = parse_log_file(log_file)
        
        for entry in entries:
            stats["total_runs"] += 1
            
            # Check if run was successful
            is_success = entry.get("report", {}).get("parse_error") is None
            
            if is_success:
                stats["successful_runs"] += 1
            else:
                stats["failed_runs"] += 1
            
            # Track runtime
            runtime = entry.get("runtime_seconds", 0)
            stats["total_runtime_seconds"] += runtime
            
            # Track tokens
            tokens = entry.get("tokens_used", 0)
            stats["total_tokens"] += tokens
            
            # Track by input source
            source = entry.get("input_source", "unknown")
            stats["by_input_source"][source]["count"] += 1
            if is_success:
                stats["by_input_source"][source]["success"] += 1
            else:
                stats["by_input_source"][source]["fail"] += 1
            
            # Track by date
            timestamp = entry.get("timestamp", "")
            if timestamp:
                date = timestamp.split("T")[0]
                stats["by_date"][date]["count"] += 1
                if is_success:
                    stats["by_date"][date]["success"] += 1
                else:
                    stats["by_date"][date]["fail"] += 1
    
    # Calculate averages
    if stats["total_runs"] > 0:
        stats["avg_runtime_seconds"] = stats["total_runtime_seconds"] / stats["total_runs"]
        stats["avg_tokens"] = stats["total_tokens"] / stats["total_runs"]
    
    # Convert defaultdicts to dicts for JSON serialization
    stats["by_input_source"] = dict(stats["by_input_source"])
    stats["by_date"] = dict(stats["by_date"])
    
    # Calculate failure rate
    if stats["total_runs"] > 0:
        stats["failure_rate_percent"] = (stats["failed_runs"] / stats["total_runs"]) * 100
    else:
        stats["failure_rate_percent"] = 0
    
    return stats


def generate_report(stats: Dict[str, Any]) -> str:
    """Generate a human-readable report from statistics."""
    report = []
    report.append("=" * 60)
    report.append("PM Digital Twin - Run Statistics Report")
    report.append("=" * 60)
    report.append("")
    
    report.append("OVERALL STATISTICS")
    report.append("-" * 40)
    report.append(f"Total Runs:        {stats['total_runs']}")
    report.append(f"Successful:        {stats['successful_runs']}")
    report.append(f"Failed:            {stats['failed_runs']}")
    report.append(f"Failure Rate:      {stats['failure_rate_percent']:.1f}%")
    report.append(f"Avg Runtime:       {stats['avg_runtime_seconds']:.2f}s")
    report.append(f"Avg Tokens:        {stats['avg_tokens']:.0f}")
    report.append("")
    
    report.append("BY INPUT SOURCE")
    report.append("-" * 40)
    for source, source_stats in sorted(stats["by_input_source"].items()):
        success_rate = (source_stats["success"] / source_stats["count"] * 100) if source_stats["count"] > 0 else 0
        report.append(f"{source}:")
        report.append(f"  Total: {source_stats['count']}, Success: {source_stats['success']}, Fail: {source_stats['fail']} ({success_rate:.1f}% success)")
    report.append("")
    
    report.append("BY DATE")
    report.append("-" * 40)
    for date, date_stats in sorted(stats["by_date"].items()):
        success_rate = (date_stats["success"] / date_stats["count"] * 100) if date_stats["count"] > 0 else 0
        report.append(f"{date}: {date_stats['count']} runs ({success_rate:.1f}% success)")
    
    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Analyze PM Digital Twin run logs")
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="Directory containing log files (default: logs)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output file for report (default: print to stdout)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of human-readable"
    )
    
    args = parser.parse_args()
    
    log_dir = Path(args.log_dir)
    if not log_dir.exists():
        print(f"Error: Log directory '{log_dir}' does not exist")
        return 1
    
    stats = analyze_runs(log_dir)
    
    if args.json:
        print(json.dumps(stats, indent=2))
    else:
        report = generate_report(stats)
        if args.output:
            Path(args.output).write_text(report)
            print(f"Report written to {args.output}")
        else:
            print(report)
    
    return 0


if __name__ == "__main__":
    exit(main())
