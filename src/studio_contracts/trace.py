"""TraceEvent contract (R-SPEC A1#2, umbrella-contract.md:118-136) — bút DE.

Owner: DE bút + sink; every node (AIE-1 executor) emits a TraceEvent. `cost`
must be the SAME number surfaced on all 3 downstream surfaces (UI test/trace/
dashboard) — a mismatch there is a bug in a consumer, not in this contract.
"""

from __future__ import annotations

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
    tenant: str  # NOT NULL, INV-1
    node_id: str
    node_type: NodeType
    ts: str  # iso8601, monotonic within a run
    inputs_hash: str
    outputs: dict[str, object]
    tokens: Tokens
    cost: float
    citations: list[str] | None = None  # from kb-retrieve
