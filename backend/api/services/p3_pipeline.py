"""
Singleton wrapper for PipelineOrchestrator.

Initialized once at app startup via lifespan (backend/api/main.py).
Reports router imports get_orchestrator() — never imports main.py directly.
"""

from __future__ import annotations

from typing import Optional

from agent.orchestrator import PipelineOrchestrator

_orchestrator: Optional[PipelineOrchestrator] = None


def get_orchestrator() -> PipelineOrchestrator:
    if _orchestrator is None:
        raise RuntimeError("P3 orchestrator not initialized — check app lifespan setup")
    return _orchestrator


async def setup() -> None:
    global _orchestrator
    _orchestrator = PipelineOrchestrator()
    await _orchestrator.setup()


async def teardown() -> None:
    global _orchestrator
    if _orchestrator is not None:
        await _orchestrator.teardown()
        _orchestrator = None
