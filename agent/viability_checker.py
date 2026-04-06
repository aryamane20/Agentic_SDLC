"""
PM Digital Twin — Viability Checker
Handles conditional viability checks based on input constraints.

Logic:
- Budget provided + Deadline provided: Check both constraints
- Budget only: Check budget constraint only
- Deadline only: Check timeline constraint only
- Neither: Skip viability check (not a failure)
"""

import re
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class InputConstraints:
    """Extracted constraints from project requirements input."""
    budget: Optional[float] = None
    deadline_weeks: Optional[float] = None
    has_budget: bool = False
    has_deadline: bool = False


@dataclass
class ViabilityResult:
    """Result of viability assessment."""
    viability_status: str  # VIABLE, AT_RISK, NOT_VIABLE, CANNOT_ASSESS
    gap_type: str  # BUDGET, SCHEDULE, BOTH, N/A
    gap_amount: str
    scoping_options: Optional[List[Dict[str, str]]] = None


class ViabilityChecker:
    """
    Performs conditional viability checks based on provided constraints.
    
    Thresholds:
    - Budget: NOT_VIABLE if estimated_cost > budget × 1.5
    - Schedule: NOT_VIABLE if critical_path_duration > deadline × 1.3
              AT_RISK if between 1.0-1.3
    """
    
    BUDGET_THRESHOLD = 1.5  # 50% over budget = NOT_VIABLE
    SCHEDULE_NOT_VIABLE_THRESHOLD = 1.3  # 30% past deadline = NOT_VIABLE
    SCHEDULE_AT_RISK_THRESHOLD = 1.0  # At or past deadline = AT_RISK
    
    def __init__(self):
        pass
    
    def check_viability(
        self, 
        raw_input: str, 
        report: Dict[str, Any]
    ) -> Optional[ViabilityResult]:
        """
        Perform viability check based on input constraints.
        
        Args:
            raw_input: Raw project requirements text
            report: Generated PM report
            
        Returns:
            ViabilityResult if constraints provided, None otherwise
        """
        # Extract constraints from input
        constraints = self._extract_constraints(raw_input)
        
        # If neither constraint provided, skip viability check
        if not constraints.has_budget and not constraints.has_deadline:
            return None
        
        # Extract project metrics from report
        estimated_cost = self._extract_estimated_cost(report)
        critical_path_duration = self._extract_critical_path_duration(report)
        
        # Perform checks based on what constraints exist
        budget_gap = None
        schedule_gap = None
        
        # Check budget if provided
        if constraints.has_budget and constraints.budget and estimated_cost:
            if estimated_cost > constraints.budget * self.BUDGET_THRESHOLD:
                budget_gap = estimated_cost - constraints.budget
            elif estimated_cost > constraints.budget:
                # Over budget but within threshold - still viable
                pass
        
        # Check schedule if provided
        if constraints.has_deadline and constraints.deadline_weeks and critical_path_duration:
            if critical_path_duration > constraints.deadline_weeks * self.SCHEDULE_NOT_VIABLE_THRESHOLD:
                schedule_gap = critical_path_duration - constraints.deadline_weeks
            elif critical_path_duration > constraints.deadline_weeks * self.SCHEDULE_AT_RISK_THRESHOLD:
                schedule_gap = critical_path_duration - constraints.deadline_weeks
        
        # Determine overall status
        return self._determine_viability_status(
            budget_gap=budget_gap,
            schedule_gap=schedule_gap,
            constraints=constraints,
            estimated_cost=estimated_cost,
            critical_path_duration=critical_path_duration
        )
    
    def _extract_constraints(self, raw_input: str) -> InputConstraints:
        """Extract budget and deadline from raw input text.
        
        Key challenge: Extract ONLY explicit budget/deadline constraints while
        avoiding false positives from mentions like "1 million users" or "400k lines".
        """
        constraints = InputConstraints()
        
        # === BUDGET EXTRACTION ===
        # Look for explicit budget mentions with dollar signs or "budget" keyword
        # Handle both plain text and markdown formats like "**Budget:** $5,000"
        
        # Pattern 1: "Budget: $5,000" or "**Budget:** $5,000" (with optional markdown)
        budget_dollar_pattern = r'[Bb]udget.*?\$\s*([\d,]+(?:\.\d{2})?)'
        match = re.search(budget_dollar_pattern, raw_input)
        if match:
            value_str = match.group(1).replace(',', '')
            try:
                constraints.budget = float(value_str)
                constraints.has_budget = True
            except ValueError:
                pass
        
        # Pattern 2: "$50k budget" or "$50K budget" (k suffix)
        if not constraints.has_budget:
            budget_k_pattern = r'\$\s*([\d,]+)\s*k(?:b)?\s*(?:budget|allocated|approved|only|remaining|total)?'
            match = re.search(budget_k_pattern, raw_input, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(',', '')
                try:
                    constraints.budget = float(value_str) * 1000
                    constraints.has_budget = True
                except ValueError:
                    pass
        
        # Pattern 3: "budget is 50k" or "budget: 50k"
        if not constraints.has_budget:
            budget_keyword_pattern = r'budget[:\s]+(?:is\s+)?([\d,]+)\s*k\b'
            match = re.search(budget_keyword_pattern, raw_input, re.IGNORECASE)
            if match:
                value_str = match.group(1).replace(',', '')
                try:
                    constraints.budget = float(value_str) * 1000
                    constraints.has_budget = True
                except ValueError:
                    pass
        
        # === DEADLINE EXTRACTION ===
        # Look for explicit deadline/timeline mentions
        
        # Use a simple, flexible pattern that handles both plain and markdown formats
        # Pattern: "Deadline" followed by number and time unit
        
        # Combined pattern: "Deadline" + optional markdown + ":" + number + unit
        deadline_combined_pattern = r'[Dd]eadline.*?(\d+)\s*(?:weeks?|w|months?|m)\b'
        match = re.search(deadline_combined_pattern, raw_input)
        if match:
            try:
                value = float(match.group(1))
                # Check if it's months
                if 'month' in match.group(0).lower():
                    value *= 4  # Convert to weeks
                constraints.deadline_weeks = value
                constraints.has_deadline = True
            except ValueError:
                pass
        
        # Pattern 2: "launch within 2 weeks" or "complete within 2 weeks"
        if not constraints.has_deadline:
            within_pattern = r'within\s+(\d+)\s*(?:weeks?|w|months?|m)\b'
            match = re.search(within_pattern, raw_input, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    if 'month' in match.group(0).lower():
                        value *= 4
                    constraints.deadline_weeks = value
                    constraints.has_deadline = True
                except ValueError:
                    pass
        
        # Pattern 3: "must be completed in 2 weeks"
        if not constraints.has_deadline:
            must_complete_pattern = r'(?:must be\s+)?completed?\s+(?:in\s+)?(\d+)\s*(?:weeks?|w|months?|m)\b'
            match = re.search(must_complete_pattern, raw_input, re.IGNORECASE)
            if match:
                try:
                    value = float(match.group(1))
                    if 'month' in match.group(0).lower():
                        value *= 4
                    constraints.deadline_weeks = value
                    constraints.has_deadline = True
                except ValueError:
                    pass
        
        return constraints
    
    def _extract_estimated_cost(self, report: Dict[str, Any]) -> Optional[float]:
        """Extract estimated total cost from the report."""
        # Try to find in project_plan
        project_plan = report.get("project_plan", {})
        
        # Check for total_cost or estimated_cost fields
        total_cost = project_plan.get("total_cost") or project_plan.get("estimated_cost")
        if total_cost:
            return self._parse_cost(total_cost)
        
        # Calculate from staffing plan
        staffing = report.get("staffing_plan", [])
        if staffing:
            total = 0
            for person in staffing:
                hours = person.get("total_hours", 0)
                # Assume average hourly rate of $100 if not specified
                rate = person.get("hourly_rate", 100)
                total += hours * rate
            return total if total > 0 else None
        
        return None
    
    def _extract_critical_path_duration(self, report: Dict[str, Any]) -> Optional[float]:
        """Extract critical path duration in weeks from report."""
        project_plan = report.get("project_plan", {})
        
        # Try critical_path_summary first
        cp_summary = project_plan.get("critical_path_summary", {})
        if cp_summary:
            duration = cp_summary.get("total_duration_days")
            if duration:
                # Tasks are sized in working days; a week = 5 working days (not calendar /7).
                return float(duration) / 5.0
        
        # Fall back to total_duration_weeks
        total_duration = project_plan.get("total_duration_weeks")
        if total_duration:
            return float(total_duration)
        
        # Calculate from phases
        phases = project_plan.get("phases", [])
        if phases:
            total = sum(p.get("duration_weeks", 0) for p in phases)
            return total if total > 0 else None
        
        return None
    
    def _parse_cost(self, cost: Any) -> Optional[float]:
        """Parse cost value from various formats."""
        if isinstance(cost, (int, float)):
            return float(cost)
        
        if isinstance(cost, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r'[\$£€,\s]', '', cost)
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        return None
    
    def _determine_viability_status(
        self,
        budget_gap: Optional[float],
        schedule_gap: Optional[float],
        constraints: InputConstraints,
        estimated_cost: Optional[float],
        critical_path_duration: Optional[float]
    ) -> ViabilityResult:
        """Determine overall viability status based on gaps found."""
        
        # Determine gap type
        gap_types = []
        gap_amounts = []
        
        if budget_gap is not None and budget_gap > 0:
            gap_types.append("BUDGET")
            gap_amounts.append(f"${budget_gap:,.0f} over budget")
        
        if schedule_gap is not None and schedule_gap > 0:
            gap_types.append("SCHEDULE")
            gap_amounts.append(f"{schedule_gap:.1f} weeks past deadline")
        
        # Determine status
        if "BUDGET" in gap_types or "SCHEDULE" in gap_types:
            # Check if any gap pushes to NOT_VIABLE
            if budget_gap and budget_gap > 0:
                # Already determined > threshold
                status = "NOT_VIABLE"
            elif schedule_gap and schedule_gap > 0:
                # Already past threshold
                status = "NOT_VIABLE"
            else:
                status = "AT_RISK"
            
            # Generate gap amount string
            gap_amount = " | ".join(gap_amounts) if gap_amounts else "N/A"
            gap_type = "BOTH" if len(gap_types) > 1 else gap_types[0]
            
            # Generate scoping options if NOT_VIABLE
            scoping_options = None
            if status == "NOT_VIABLE":
                scoping_options = self._generate_scoping_options(
                    gap_type=gap_type,
                    budget_gap=budget_gap,
                    schedule_gap=schedule_gap,
                    constraints=constraints
                )
            
            return ViabilityResult(
                viability_status=status,
                gap_type=gap_type,
                gap_amount=gap_amount,
                scoping_options=scoping_options
            )
        
        # No gaps - VIABLE
        return ViabilityResult(
            viability_status="VIABLE",
            gap_type="N/A",
            gap_amount="N/A",
            scoping_options=None
        )
    
    def _generate_scoping_options(
        self,
        gap_type: str,
        budget_gap: Optional[float],
        schedule_gap: Optional[float],
        constraints: InputConstraints
    ) -> List[Dict[str, str]]:
        """Generate scoping options to close the gap."""
        options = []
        
        if gap_type in ["BUDGET", "BOTH"]:
            # Budget gap options
            options.extend([
                {
                    "option_id": "B1",
                    "description": "Reduce scope - remove non-essential features",
                    "impact": f"Reduce estimated cost by ${budget_gap*0.3:,.0f} if 30% of features deferred",
                    "tradeoffs": "Delayed functionality, potential user dissatisfaction"
                },
                {
                    "option_id": "B2", 
                    "description": "Extend timeline to reduce peak resource needs",
                    "impact": "Reduce resource costs by spreading work over longer period",
                    "tradeoffs": "Longer time to value, potential market window loss"
                },
                {
                    "option_id": "B3",
                    "description": "Negotiate additional budget with stakeholders",
                    "impact": "Close budget gap fully if approved",
                    "tradeoffs": "Requires executive approval, may affect other projects"
                }
            ])
        
        if gap_type in ["SCHEDULE", "BOTH"]:
            # Schedule gap options
            options.extend([
                {
                    "option_id": "S1",
                    "description": "Add resources - increase team size",
                    "impact": f"Reduce timeline by {schedule_gap*0.5:.1f} weeks with 50% more resources",
                    "tradeoffs": "Increased cost, potential coordination overhead"
                },
                {
                    "option_id": "S2",
                    "description": "Phase delivery - release MVP first",
                    "impact": f"Core features in {constraints.deadline_weeks:.0f} weeks, full scope later",
                    "tradeoffs": "Partial functionality at launch, technical debt"
                },
                {
                    "option_id": "S3",
                    "description": "Negotiate deadline extension",
                    "impact": f"Extend to {constraints.deadline_weeks + schedule_gap:.0f} weeks",
                    "tradeoffs": "Requires stakeholder buy-in, may miss market window"
                }
            ])
        
        # Return top 3 options
        return options[:3]


def check_viability(raw_input: str, report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Convenience function to check viability.
    
    Args:
        raw_input: Raw project requirements text
        report: Generated PM report
        
    Returns:
        Viability dict if constraints provided, None otherwise
    """
    checker = ViabilityChecker()
    result = checker.check_viability(raw_input, report)
    
    if result is None:
        return None
    
    return {
        "viability_status": result.viability_status,
        "gap_type": result.gap_type,
        "gap_amount": result.gap_amount,
        "scoping_options": result.scoping_options
    }
