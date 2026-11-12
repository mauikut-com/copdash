"""Verdict engine interface.

Every engine — the current rules engine and the future SimPy engine — implements
this ``Protocol``, so the HTTP layer and the registry don't care which engine
they're talking to.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.schemas import EvaluationInput, VerdictResult


@runtime_checkable
class VerdictEngine(Protocol):
    """Anything that can turn a spec + load into a verdict."""

    name: str

    def evaluate(self, input: EvaluationInput) -> VerdictResult:
        """Evaluate the load against the spec and return a verdict."""
        ...
