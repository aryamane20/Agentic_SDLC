"""
PM Digital Twin — Agent Core
Handles: prompt loading, knowledge base compilation, LLM call, JSON extraction

ARCHITECTURE NOTE:
  Role (HOW to think)      → prompts/vN_system.txt
  Knowledge Base (WHAT to know) → knowledge-base/{templates,risks,staffing}/

  These are compiled into one context at runtime by _build_system_context().
  They are kept separate so reasoning changes and domain knowledge changes
  can be tracked independently in git and evaluated independently.

  Project 1: All knowledge base files loaded inline (no RAG)
  Project 3: This compiler will be replaced with RAG retrieval per sub-agent
"""

import hashlib
import json
import os
import re
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()  # load .env before other imports that read env vars

import anthropic
from langfuse import Langfuse, observe

CACHE_DIR = Path("outputs/.cache")


# Knowledge base file paths — update here if structure changes
KNOWLEDGE_BASE = {
    "templates": "knowledge-base/templates/project-type-templates.md",
    "risks":     "knowledge-base/risks/risk-patterns.md",
    "staffing":  "knowledge-base/staffing/role-definitions.md",
}

# Model constants — use HAIKU for prompt iteration and debugging,
# SONNET for official eval runs and Demo Day outputs.
# NOTE: This API key only has access to claude-sonnet-4. Both constants
# point to Sonnet until a Haiku 4 model is released or a key with
# broader model access is available.
MODEL_HAIKU  = "claude-haiku-4-5-20251001"
MODEL_SONNET = "claude-sonnet-4-20250514"


class PMAgent:
    """
    The PM Digital Twin agent.
    Compiles role + knowledge base into a single context, then runs
    the 8-step PM reasoning process on raw requirements input.
    """

    def __init__(self, prompt_version: str = "v1.6.1", model: str = MODEL_HAIKU):
        self.prompt_version = prompt_version
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.langfuse = Langfuse()  # reads LANGFUSE_* from env; no-ops if keys missing
        self.model = model
        self.temperature = 0.0   # Greedy decoding for maximum consistency (D2 fix)
        self.max_tokens = 16000   # Haiku produces verbose JSON (~8-12k tokens); needs headroom to avoid truncation
        self.system_prompt = self._build_system_context()

    def _load_role(self) -> str:
        """
        Load the versioned role file.
        The role encodes: WHO the agent is, HOW it thinks, WHAT it never does.
        Change this when reasoning quality or behavior needs to improve.
        """
        role_path = Path(f"prompts/v{self.prompt_version.replace('v', '')}_system.txt")
        if not role_path.exists():
            raise FileNotFoundError(
                f"Role file not found: {role_path}\n"
                f"Available versions: {list(Path('prompts').glob('v*_system.txt'))}"
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

    def _cache_key(self, raw_input: str) -> str:
        """Deterministic hash of (prompt_version, model, temperature, input)."""
        payload = f"{self.prompt_version}|{self.model}|{self.temperature}|{raw_input}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def _load_from_cache(self, key: str) -> dict | None:
        path = CACHE_DIR / f"{key}.json"
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return None

    def _save_to_cache(self, key: str, result: dict):
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path = CACHE_DIR / f"{key}.json"
        with open(path, "w") as f:
            json.dump(result, f, indent=2)

    @observe(name="pm-agent-run")
    def run(self, raw_input: str, input_source: str = "unknown",
            use_cache: bool = True) -> dict:
        """
        Run the PM agent on raw requirements input.

        Args:
            raw_input: Any freeform project requirements text
            input_source: Optional label for tracing (e.g. 'tc-01', 'streamlit-ui')
            use_cache: If True, return cached result for identical input+prompt+model.
                       Set False for consistency testing (D2) or when you need fresh output.

        Returns:
            dict with 'report' (parsed JSON), 'tokens_used', 'input_tokens',
            'output_tokens', 'cache_read_tokens', 'cache_creation_tokens'
        """
        cache_key = self._cache_key(raw_input)

        if use_cache:
            cached = self._load_from_cache(cache_key)
            if cached is not None:
                cached["cache_hit"] = True
                return cached

        # Langfuse: update current observation with input + metadata.
        # If langfuse.decorators exists, use: langfuse_context.update_current_observation(...)
        self.langfuse.update_current_span(
            name=f"pm-run-{self.prompt_version}",
            input=raw_input,
            metadata={
                "prompt_version": self.prompt_version,
                "model": self.model,
                "input_source": input_source,
                "temperature": self.temperature,
            },
        )

        user_message = self._build_user_message(raw_input)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=[
                {
                    "type": "text",
                    "text": self.system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
            stream=False,
        )

        raw_output = response.content[0].text
        usage = response.usage
        input_tokens = usage.input_tokens
        output_tokens = usage.output_tokens
        tokens_used = input_tokens + output_tokens
        cache_read_tokens = getattr(usage, "cache_read_input_tokens", 0)
        cache_creation_tokens = getattr(usage, "cache_creation_input_tokens", 0)

        report = self._extract_json(raw_output)
        parse_failed = report.get("parse_error", False)

        if not parse_failed:
            self._enforce_hard_caps(report)

        self.langfuse.update_current_span(
            output=report,
            metadata={
                "tokens_used": tokens_used,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "parse_failed": parse_failed,
            },
        )

        if "report_metadata" not in report:
            report["report_metadata"] = {}
        report["report_metadata"]["generated_at"] = datetime.utcnow().isoformat() + "Z"
        report["report_metadata"]["prompt_version"] = self.prompt_version

        result = {
            "report": report,
            "raw_output": raw_output,
            "tokens_used": tokens_used,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read_tokens": cache_read_tokens,
            "cache_creation_tokens": cache_creation_tokens,
            "cache_hit": False,
        }

        if use_cache and not parse_failed:
            self._save_to_cache(cache_key, result)

        return result

    def _build_user_message(self, raw_input: str) -> str:
        """
        Wraps raw input with instructions to trigger 8-step reasoning.
        """
        return f"""Analyze the following project requirements using your full 8-step reasoning process.

Output a single valid JSON object only. No prose. No section headers. No markdown. Just the JSON.

PROJECT REQUIREMENTS:
---
{raw_input}
---

Begin."""

    def _enforce_hard_caps(self, report: dict):
        """
        Post-processing safety net: mechanically enforce hard cap rules
        that the prompt instructs the LLM to follow but it often doesn't.

        Caps (applied strictest-first):
          - assumption_count >= 8 → score <= 40
          - assumption_count >= 5 → score <= 60
          - CRITICAL risk + assumptions >= 3 → score <= 50
        """
        assumptions = report.get("assumption_log", [])
        assumption_count = len(assumptions)
        risks = report.get("risk_register", [])
        has_critical = any(r.get("score") == "CRITICAL" for r in risks)

        cap = 100
        cap_reasons = []
        if assumption_count >= 8:
            cap = min(cap, 40)
            cap_reasons.append(f">=8 assumptions ({assumption_count}) -> cap 40")
        elif assumption_count >= 5:
            cap = min(cap, 60)
            cap_reasons.append(f">=5 assumptions ({assumption_count}) -> cap 60")
        if has_critical and assumption_count >= 3:
            cap = min(cap, 50)
            cap_reasons.append(f"CRITICAL risk + >=3 assumptions -> cap 50")

        cs = report.get("pm_confidence_score", {})
        if isinstance(cs, dict):
            original = cs.get("score", 0)
            if original > cap:
                cs["score"] = cap
                cs.setdefault("deductions", []).append({
                    "amount": original - cap,
                    "reason": f"Hard cap enforced by post-processing: {'; '.join(cap_reasons)}"
                })
            report["pm_confidence_score"] = cs
            if "report_metadata" in report:
                report["report_metadata"]["pm_confidence_score"] = cs["score"]
        elif isinstance(cs, (int, float)):
            if cs > cap:
                report["pm_confidence_score"] = {"score": cap, "deductions": [{
                    "amount": cs - cap,
                    "reason": f"Hard cap enforced by post-processing: {'; '.join(cap_reasons)}"
                }]}
                if "report_metadata" in report:
                    report["report_metadata"]["pm_confidence_score"] = cap

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
