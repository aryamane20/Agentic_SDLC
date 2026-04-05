"""Request-scoped dependencies (e.g. per-browser plan namespace)."""

from __future__ import annotations

import hashlib
import re

from fastapi import Header

_USER_TOKEN = re.compile(r"^[a-zA-Z0-9_-]{1,128}$")


def planr_user_id(x_planr_user: str | None = Header(None, alias="X-Planr-User")) -> str:
    """
    Isolates JSON sessions on disk per caller. The web app sends a stable UUID from
    localStorage; API clients may omit the header (namespace 'anonymous').
    """
    if not x_planr_user or not (t := x_planr_user.strip()):
        return "anonymous"
    if _USER_TOKEN.match(t):
        return t
    return hashlib.sha256(t.encode()).hexdigest()[:32]
