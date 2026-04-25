import re
from typing import Literal, Optional

from pydantic import BaseModel

_PROFANITY = frozenset({
    "fuck", "fucking", "shit", "bitch", "asshole", "bastard",
    "cunt", "dick", "piss", "damn", "crap", "motherfucker",
    "fucker", "bullshit", "ass", "stupid",
})

_PROJECT_SIGNALS = frozenset({
    "build", "dashboard", "pipeline", "migrate", "portal", "api",
    "feature", "users", "workflow", "workflows", "platform", "service", "system",
    "app", "tool", "integration", "database", "deploy", "backend",
    "frontend", "module", "product", "redesign", "automate", "tracker", "report",
    # Common verb/noun stems missed by the original list — drove false
    # `no_project_signal` flags on hp-02 (scenario-b-low-confidence) and
    # hp-06 (tc-04-vague). See test_intake_contract for guarded cases.
    "track", "tracking", "project", "projects", "team", "teams",
    "manage", "manager",
})

# Word tokenizer used by Rules 5 and 10. Plain `text.lower().split()` keeps
# punctuation glued to tokens (e.g. "app?" → "app?") and silently breaks
# membership checks against _PROJECT_SIGNALS / _PROFANITY. This regex pulls
# alphabetic-only tokens (with optional inner apostrophe) so "app?" → "app".
_TOKEN_RE = re.compile(r"[a-z]+(?:'[a-z]+)?")

_RULES: list[tuple[str, Literal["REFUSED", "NEEDS_BRIEF"], str, list[re.Pattern]]] = []


def _c(pattern: str, flags: int = re.IGNORECASE | re.DOTALL) -> re.Pattern:
    return re.compile(pattern, flags)


_INJECTION_PATTERNS = [
    _c(r"ignore\s+.{0,30}(previous|prior|above)\s+instructions"),
    _c(r"\bdisregard\b.{0,60}instructions"),
    _c(r"<\/?(system|json|prompt)>"),
    _c(r"</\w+>\s*\{"),
]
_ROLE_SWITCH_PATTERNS = [
    _c(r"you\s+are\s+(no\s+longer|not)\s+.{0,30}(agent|assistant)"),
    _c(r"you\s+are\s+(now\s+)?(DAN|dan)\b"),
]
_EXTRACTION_PATTERNS = [
    _c(r"(print|show|reveal|output).{0,30}(system|full)\s+prompt"),
    _c(r"list\s+(all|the)\s+instructions"),
    _c(r"repeat\s+(everything|all)\s+above"),
    _c(r"before\s+the\s+plan.{0,60}list\s+all\s+the\s+instructions"),
]
_CROSS_SESSION_PATTERNS = [
    _c(r"(show|list).{0,40}(previous|other|past).{0,40}(sessions?|users?)"),
    _c(r"other\s+user.?s\s+data"),
]
_UNETHICAL_PATTERNS = [
    _c(r"surveillance.{0,40}(without\s+consent|covert)"),
    _c(r"(spy\s+on|track)\s+(my\s+(wife|spouse|partner)|employees)\s+without"),
    _c(r"covert\s+surveillance"),
]
_URL_ONLY = _c(r"^https?://\S+$")

_MSG_NEEDS_BRIEF = "Describe what you want to build, for whom, and why — then try again."
_MSG_REFUSED = "This input can't be processed. Please submit a project description."


class IntakeVerdict(BaseModel):
    verdict: Literal["OK", "NEEDS_BRIEF", "REFUSED"]
    reason_code: Optional[str] = None
    user_message: str
    matched_pattern: Optional[str] = None


def _any_match(patterns: list[re.Pattern], text: str) -> Optional[str]:
    for p in patterns:
        m = p.search(text)
        if m:
            return m.group(0)
    return None


def classify_input(text: str, prd_text: str = "") -> IntakeVerdict:
    has_prd = bool(prd_text.strip())

    # Rule 1: prompt injection
    match = _any_match(_INJECTION_PATTERNS, text)
    if match:
        return IntakeVerdict(verdict="REFUSED", reason_code="prompt_injection",
                             user_message=_MSG_REFUSED, matched_pattern=match)

    # Rule 2: role switch
    match = _any_match(_ROLE_SWITCH_PATTERNS, text)
    if match:
        return IntakeVerdict(verdict="REFUSED", reason_code="role_switch",
                             user_message=_MSG_REFUSED, matched_pattern=match)

    # Rule 3: system prompt extraction
    match = _any_match(_EXTRACTION_PATTERNS, text)
    if match:
        return IntakeVerdict(verdict="REFUSED", reason_code="system_prompt_extraction",
                             user_message=_MSG_REFUSED, matched_pattern=match)

    # Rule 4: cross-session data extraction
    match = _any_match(_CROSS_SESSION_PATTERNS, text)
    if match:
        return IntakeVerdict(verdict="REFUSED", reason_code="cross_session_extraction",
                             user_message=_MSG_REFUSED, matched_pattern=match)

    # Rule 5: abuse without a real project.
    # Intentionally passes gr-03 (abusive tone + real project brief) by checking for
    # project keywords rather than input length. A malicious input with a project
    # keyword appended will also pass — this is a known, documented limitation.
    # Do not tighten this rule without re-running test_input_guard.py gr-03.
    # Tokenize via _TOKEN_RE so trailing punctuation ("app?", "Fuck,") doesn't
    # silently break membership lookups against _PROJECT_SIGNALS / _PROFANITY.
    words = set(_TOKEN_RE.findall(text.lower()))
    if words & _PROFANITY and not (words & _PROJECT_SIGNALS):
        return IntakeVerdict(verdict="REFUSED", reason_code="abuse",
                             user_message=_MSG_REFUSED)

    # Rule 6: unethical project
    match = _any_match(_UNETHICAL_PATTERNS, text)
    if match:
        return IntakeVerdict(verdict="REFUSED", reason_code="unethical_project",
                             user_message=_MSG_REFUSED, matched_pattern=match)

    # Rules 7–10 are waived if a PRD is attached
    if not has_prd:
        # Rule 7: empty
        if not text.strip():
            return IntakeVerdict(verdict="NEEDS_BRIEF", reason_code="empty",
                                 user_message=_MSG_NEEDS_BRIEF)

        # Rule 8: URL only (before too_short — a URL is one token, would hit too_short first)
        if _URL_ONLY.match(text.strip()):
            return IntakeVerdict(verdict="NEEDS_BRIEF", reason_code="url_only",
                                 user_message=_MSG_NEEDS_BRIEF)

        # Rule 9: too short
        if len(text.strip().split()) < 3:
            return IntakeVerdict(verdict="NEEDS_BRIEF", reason_code="too_short",
                                 user_message=_MSG_NEEDS_BRIEF)

        # Rule 10: no project signal
        if not (words & _PROJECT_SIGNALS):
            return IntakeVerdict(verdict="NEEDS_BRIEF", reason_code="no_project_signal",
                                 user_message=_MSG_NEEDS_BRIEF)

    # Rule 11: OK
    return IntakeVerdict(verdict="OK", user_message="")
