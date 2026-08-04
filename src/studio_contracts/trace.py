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
    """Chunk ids the answer actually GROUNDS on. "retrieved" and "cited/grounded" are
    different facts: kb-retrieve's scope-filtered chunks (which may be irrelevant to the
    answer) live in `outputs["chunks"]`; this field carries only what the answer actually
    used, which is what citation-accuracy / leak-check scoring (evalhub) depends on.

    Set by the output's RETURN-TYPE, not by node_type: the interpreter fills `citations`
    from `outputs.get("citations")` when a node returns a dict, and leaves it `None` when a
    node returns a list (see engine interpreter.py:265). kb-retrieve returns a list, so its
    event is always `None` — but that follows from the return-type rule, not from a node_type
    check. Today only `llm-step` returns a dict carrying "citations", so in practice only its
    event is populated; this is COINCIDENTAL, not engine-enforced — any node returning a dict
    with a "citations" key would carry it (mutation M1, kit#131: 0 layers catch a violation).
    Making "llm-step only" a real guarantee needs node_type gating in the interpreter + a test,
    not a contract comment. Replaces a stale `# from kb-retrieve` comment that did not match
    interpreter (AIE-1) behavior — see agentcore-studio-kit issue #84 decision-log."""
