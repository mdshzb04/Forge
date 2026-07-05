"""Typed context that flows through the engine's eight stages.

Each stage reads from the context, mutates one or two fields, and
returns a :class:`~forgecli.engine.execution.StageResult`. The
context is the *only* mechanism stages use to share data — there
are no hidden globals.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from forgecli.plugins import Intent

# ---------------------------------------------------------------------------
# Per-stage payloads
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntentAnalysis:
    """The output of the Intent Analyzer stage."""

    intent: Intent
    confidence: float
    rationale: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievalResult:
    """The output of the Repository Analyzer stage."""

    query: str
    matched_nodes: tuple[Mapping[str, Any], ...] = ()
    context_text: str = ""
    artifacts: dict[str, Path] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ModelSelection:
    """The output of the Model Router stage."""

    provider: str
    model: str
    mode: str = "explicit"  # "explicit" | "cheapest" | "fallback"
    cost_in: float = 0.0
    cost_out: float = 0.0


@dataclass(frozen=True)
class StageLog:
    """A single record of how a stage performed.

    The engine accumulates these on :class:`EngineContext` so
    callers can render a final report.
    """

    stage: str
    status: str
    started_at: float
    finished_at: float | None = None
    notes: tuple[str, ...] = ()
    error: str | None = None

    @property
    def duration_seconds(self) -> float:
        if self.finished_at is None:
            return 0.0
        return max(0.0, self.finished_at - self.started_at)


# ---------------------------------------------------------------------------
# Engine context
# ---------------------------------------------------------------------------


@dataclass
class EngineContext:
    """Mutable state shared by every stage of the engine.

    The context is constructed by :class:`EngineBuilder` and
    passed to each :class:`Stage`. Stages may set the
    ``intent_analysis`` / ``retrieval`` / ``model_selection`` /
    ``plan`` / ``response`` / ``diff_text`` / ``applied_files`` /
    ``test_*`` fields; downstream stages read them.
    """

    prompt: str
    cwd: Path
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: float = field(default_factory=time.time)

    # Stage 1: Intent
    intent_analysis: IntentAnalysis | None = None
    # Stage 2: Retrieval
    retrieval: RetrievalResult | None = None
    # Stage 3: Caveman optimization (runs before context optimization)
    caveman_optimized_request: Any = None
    caveman_optimized_notes: tuple[str, ...] = ()
    # Stage 4: Context optimization
    optimized_request: Any = None
    optimized_notes: tuple[str, ...] = ()
    # Stage 5: Plan
    plan: Any = None  # SoftwarePlan; kept loose to avoid an import cycle
    # Stage 5: Model
    model_selection: ModelSelection | None = None
    # Stage 6: Execution
    response: Any = None
    # Stage 7: Validation
    diff_text: str = ""
    applied_files: list[Path] = field(default_factory=list)
    test_stdout: str = ""
    test_stderr: str = ""
    test_returncode: int | None = None
    fix_attempts: int = 0
    # Stage 8: Git
    staged: bool = False
    pushed: bool = False

    # Free-form extras for plugins / advanced stages.
    extras: dict[str, Any] = field(default_factory=dict)

    # Per-stage log (append-only).
    log: list[StageLog] = field(default_factory=list)

    def to_log_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of the context (no Paths)."""
        return {
            "run_id": self.run_id,
            "started_at": self.started_at,
            "intent": self.intent_analysis.intent.value if self.intent_analysis else None,
            "intent_confidence": self.intent_analysis.confidence if self.intent_analysis else 0.0,
            "retrieval_query": self.retrieval.query if self.retrieval else None,
            "retrieval_match_count": len(self.retrieval.matched_nodes) if self.retrieval else 0,
            "caveman_optimized_notes": list(self.caveman_optimized_notes),
            "optimized_notes": list(self.optimized_notes),
            "has_plan": self.plan is not None,
            "model": self.model_selection.model if self.model_selection else None,
            "provider": self.model_selection.provider if self.model_selection else None,
            "response_present": self.response is not None,
            "diff_length": len(self.diff_text),
            "applied_files": [str(p) for p in self.applied_files],
            "test_returncode": self.test_returncode,
            "fix_attempts": self.fix_attempts,
            "staged": self.staged,
            "pushed": self.pushed,
            "stage_count": len(self.log),
        }


__all__ = [
    "EngineContext",
    "IntentAnalysis",
    "ModelSelection",
    "RetrievalResult",
    "StageLog",
]
