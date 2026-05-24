"""
KBRetriever — keyword-based KB slice selection for P3 agents.

Each agent gets only the KB content it needs:
  planning  → project-type-templates.md (filtered to the matching TYPE section)
  risk      → risk-patterns.md (full)
  staffing  → role-definitions.md (full)
  others    → None (no KB needed)

Interface is designed for a future Pinecone/vector-store swap:
  replace _filter_templates_for_type() with pinecone.query(vector, top_k=3)
  and get_for_agent() stays identical — no agent code changes needed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

_KB_DIR = Path(__file__).parent.parent / "knowledge-base"

_KB_FILES = {
    "templates": _KB_DIR / "templates" / "project-type-templates.md",
    "risks":     _KB_DIR / "risks"     / "risk-patterns.md",
    "staffing":  _KB_DIR / "staffing"  / "role-definitions.md",
}


class KBRetriever:
    """
    Loads KB files once at construction and serves slices per agent.
    Instantiate once and reuse across the pipeline run.
    """

    def __init__(self) -> None:
        self._kb: dict[str, str] = {}
        for key, path in _KB_FILES.items():
            if path.exists():
                self._kb[key] = path.read_text(encoding="utf-8")
            else:
                print(f"[WARN] KB file missing: {path} — '{key}' section unavailable")
                self._kb[key] = ""

    def get_for_agent(
        self,
        agent_name: str,
        project_type: Optional[str] = None,
    ) -> Optional[str]:
        """
        Return KB content string for the given agent, or None if the agent needs no KB.

        agent_name: one of "use_case", "intake", "planning", "risk", "staffing", "synthesis"
        project_type: e.g. "TYPE_A" — used to filter the templates file for planning agent
        """
        if agent_name == "planning":
            if project_type:
                filtered = self._filter_templates_for_type(project_type)
                return filtered if filtered else self._kb["templates"]
            return self._kb["templates"]

        if agent_name == "risk":
            return self._kb["risks"]

        if agent_name == "staffing":
            return self._kb["staffing"]

        # use_case, intake, synthesis need no KB
        return None

    def _filter_templates_for_type(self, project_type: str) -> str:
        """
        Return the identity header + only the TYPE_X section from templates.md.
        Cuts Planning agent context by ~60–70% vs the full file.

        project_type: "TYPE_A" ... "TYPE_F"
        """
        content = self._kb.get("templates", "")
        if not content:
            return ""

        type_letter = project_type.split("_")[-1].upper()  # "A" ... "F"
        target_header = f"## TYPE {type_letter}"

        lines = content.splitlines()
        header_lines: list[str] = []
        section_lines: list[str] = []
        in_target = False
        preamble_done = False

        for line in lines:
            # Collect preamble (everything before the first ## TYPE block)
            if not preamble_done and not line.startswith("## TYPE "):
                header_lines.append(line)
                continue

            preamble_done = True

            if line.startswith("## TYPE "):
                if line.startswith(target_header):
                    in_target = True
                    section_lines.append(line)
                elif in_target:
                    # Hit the next TYPE block — stop
                    break
                # else: different TYPE block, skip
            elif in_target:
                section_lines.append(line)

        if not section_lines:
            # Fallback: return full content if TYPE not found
            return content

        return "\n".join(header_lines + [""] + section_lines)
