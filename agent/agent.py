"""
PM Digital Twin — Agent Core
Handles: prompt loading, knowledge base compilation, LLM call, JSON extraction

ARCHITECTURE NOTE:
  Role (HOW to think)      → agent/prompts/system_prompt_vN.md
  Knowledge Base (WHAT to know) → knowledge-base/{templates,risks,staffing}/

  These are compiled into one context at runtime by _build_system_context().
  They are kept separate so reasoning changes and domain knowledge changes
  can be tracked independently in git and evaluated independently.

  Project 1: All knowledge base files loaded inline (no RAG)
  Project 3: This compiler will be replaced with RAG retrieval per sub-agent
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime

import anthropic


# Knowledge base file paths — update here if structure changes
KNOWLEDGE_BASE = {
    "templates": "knowledge-base/templates/project-type-templates.md",
    "risks":     "knowledge-base/risks/risk-patterns.md",
    "staffing":  "knowledge-base/staffing/role-definitions.md",
}


class PMAgent:
    """
    The PM Digital Twin agent.
    Compiles role + knowledge base into a single context, then runs
    the 8-step PM reasoning process on raw requirements input.
    """

    def __init__(self, prompt_version: str = "v1"):
        self.prompt_version = prompt_version
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-20250514"
        self.temperature = 0.3   # Low for consistency (PMBOK-grounded output)
        self.max_tokens = 15000   # Increased for detailed PM reports with full JSON
        self.system_prompt = self._build_system_context()

    def _load_role(self) -> str:
        """
        Load the versioned role file.
        The role encodes: WHO the agent is, HOW it thinks, WHAT it never does.
        Change this when reasoning quality or behavior needs to improve.
        """
        role_path = Path(f"agent/prompts/system_prompt_{self.prompt_version}.md")
        if not role_path.exists():
            raise FileNotFoundError(
                f"Role file not found: {role_path}\n"
                f"Available versions: {list(Path('agent/prompts').glob('system_prompt_*.md'))}"
            )
        return role_path.read_text(encoding="utf-8")

    def _load_knowledge_base(self) -> dict:
        """
        Load all knowledge base files.
        The knowledge base encodes: WHAT domain knowledge the agent draws on.
        Change these files when domain coverage needs to improve.

        Returns dict of {section_name: content} for each KB file.
        Missing files are logged as warnings but do not crash the agent.
        """
        kb = {}
        for section, filepath in KNOWLEDGE_BASE.items():
            path = Path(filepath)
            if path.exists():
                kb[section] = path.read_text(encoding="utf-8")
            else:
                print(f"[WARN] Knowledge base file missing: {filepath} — section '{section}' skipped")
                kb[section] = f"[{section} knowledge base not loaded — file missing]"
        return kb

    def _build_system_context(self) -> str:
        """
        Compile role + knowledge base into one system context.

        Structure:
          [ROLE — always first, sets identity and reasoning process]
          ---KNOWLEDGE BASE---
          [TEMPLATES — project type specific phase additions]
          [RISKS — risk pattern catalog]
          [STAFFING — role benchmarks and effort estimates]

        In Project 3, this method will be replaced with RAG retrieval:
          kb["templates"] = vector_store.query(f"project type {classified_type}")
          kb["risks"]     = vector_store.query(f"risk patterns {classified_type}")
          kb["staffing"]  = vector_store.query(f"staffing {classified_type}")
        """
        role = self._load_role()
        kb = self._load_knowledge_base()

        context = f"""{role}

---KNOWLEDGE BASE---

## PROJECT TYPE TEMPLATES
{kb['templates']}

## RISK PATTERN CATALOG
{kb['risks']}

## STAFFING BENCHMARKS
{kb['staffing']}
---END KNOWLEDGE BASE---"""

        return context

    def run(self, raw_input: str) -> dict:
        """
        Run the PM agent on raw requirements input.

        Args:
            raw_input: Any freeform project requirements text

        Returns:
            dict with 'report' (parsed JSON), 'tokens_used', 'context_source'
        """
        user_message = self._build_user_message(raw_input)

        # Call LLM with compiled role + knowledge base context
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=self.system_prompt,   # compiled role + KB
            messages=[
                {"role": "user", "content": user_message}
            ]
        )

        raw_output = response.content[0].text
        tokens_used = response.usage.input_tokens + response.usage.output_tokens

        # Extract and parse JSON from response
        report = self._extract_json(raw_output)

        # Inject metadata if not present
        if "report_metadata" not in report:
            report["report_metadata"] = {}
        report["report_metadata"]["generated_at"] = datetime.utcnow().isoformat() + "Z"
        report["report_metadata"]["prompt_version"] = self.prompt_version

        return {
            "report": report,
            "raw_output": raw_output,
            "tokens_used": tokens_used
        }

    def _build_user_message(self, raw_input: str) -> str:
        """
        Wraps raw input with instructions to trigger 8-step reasoning.
        """
        return f"""Please analyze the following project requirements and produce a complete PM Digital Twin Report.

Follow your full 8-step reasoning process. After the human-readable report sections, output the complete JSON object matching the output schema.

PROJECT REQUIREMENTS:
---
{raw_input}
---

Begin your analysis now."""

    def _extract_json(self, raw_output: str) -> dict:
        """
        Extract the JSON object from the LLM's response.
        The LLM produces a human-readable report followed by a JSON block.
        
        Handles:
        - JSON in code blocks
        - JSON starting from first { to end of response
        - Truncated JSON (tries to fix missing closing braces)
        """
        # Strategy 1: Find JSON in code block
        code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_output, re.DOTALL)
        if code_block_match:
            try:
                return json.loads(code_block_match.group(1))
            except json.JSONDecodeError:
                pass

        # Strategy 2: Find the last large JSON object in the response
        # (LLM puts human text first, JSON last)
        json_matches = list(re.finditer(r"\{", raw_output))
        for match in reversed(json_matches):
            candidate = raw_output[match.start():]
            try:
                parsed = json.loads(candidate)
                # Validate it looks like our schema (has required top-level keys)
                if "project_understanding" in parsed or "report_metadata" in parsed:
                    return parsed
            except json.JSONDecodeError:
                # Try to fix truncated JSON by adding missing braces
                fixed = self._fix_truncated_json(candidate)
                if fixed:
                    try:
                        parsed = json.loads(fixed)
                        if "project_understanding" in parsed or "report_metadata" in parsed:
                            return parsed
                    except:
                        pass
                continue

        # Strategy 3: Try the entire output as JSON
        try:
            cleaned = raw_output.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
                cleaned = re.sub(r"```$", "", cleaned).strip()
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Fallback: return error structure
        return {
            "parse_error": True,
            "raw_output": raw_output,
            "report_metadata": {
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "parse_failed": True
            }
        }
    
    def _fix_truncated_json(self, json_str: str) -> str:
        """
        Attempt to fix truncated JSON by adding missing closing braces.
        """
        # Count open and closed braces
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        
        if open_braces > close_braces:
            # Add missing closing braces
            missing = open_braces - close_braces
            return json_str + ('}' * missing)
        
        return None
