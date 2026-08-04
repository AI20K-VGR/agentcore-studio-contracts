"""TraceEvent contract (R-SPEC A1#2, umbrella-contract.md:118-136) — bút DE.

Owner: DE bút + sink; every node (AIE-1 executor) emits a TraceEvent. `cost`
must be the SAME number surfaced on all 3 downstream surfaces (UI test/trace/
dashboard) — a mismatch there is a bug in a consumer, not in this contract.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from studio_contracts.nodes import NodeType


class Tokens(BaseModel):
    model_config = ConfigDict(frozen=True)

    prompt: int
    completion: int


class TraceEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str
    run_id: str
    agent_id: str
    tenant_id: UUID  # NOT NULL, INV-1
    node_id: str
    node_type: NodeType
    ts: str  # iso8601, monotonic within a run
    inputs_hash: str
    outputs: dict[str, object]
    tokens: Tokens
    cost: float
    citations: list[str] | None = None
    """Chunk ids the answer actually GROUNDS on — set by the `llm-step` node's event only.
    `kb-retrieve`'s own event must always leave this `None` (its retrieved chunks live in
    `outputs["chunks"]` instead): "retrieved" (kb-retrieve, scope-filtered, may be irrelevant)
    and "cited/grounded" (llm-step, what the answer actually used) are different facts, and
    citation-accuracy / leak-check scoring (evalhub) depends on this field carrying only the
    latter. D11 decision: this replaces a stale `# from kb-retrieve` comment that did not match
    actual interpreter (AIE-1) behavior — see agentcore-studio-kit issue #84 decision-log."""
