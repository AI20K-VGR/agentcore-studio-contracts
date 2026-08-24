"""AgentCore Studio contracts — frozen pydantic schemas (recipe/trace-event/
kb.search/scorecard) + the closed 6-value `NodeType` + 3 Protocol seams
(EmbeddingService/LLM/TraceWriter).

`SCHEMA_VERSION = "0.2.0-draft"` — v0-draft (Decision #7): contracts are NOT
frozen-for-real yet (S1 walking-skeleton chưa đóng); freeze happens when the
owner signs off (mini-RFC + 4/4 signatures per umbrella-contract.md §3).
Additive-only discipline applies from day one (copy pattern R-DI §4): new
OPTIONAL fields may be added without a bump; renames/removals/required-additions
are breaking and need a DEC + SCHEMA_VERSION bump. The 0.1.0→0.2.0 bump records
the first such breaking change: `tenant: str` → `tenant_id: UUID` across
kb.search/trace-event/recipe (D-13 — tenant identity = immutable UUID).

Contracts is the bottom import-layer (see `.importlinter`): this package
imports pydantic + stdlib typing ONLY — never another `studio_*` package.
"""

from studio_contracts.cost import cost_of
from studio_contracts.kb import KbSearch, KbSearchResultItem
from studio_contracts.nodes import NodeType
from studio_contracts.protocols import LLM, EmbeddingService, TraceWriter
from studio_contracts.recipe import (
    AgentConfig,
    Dag,
    Edge,
    KbBinding,
    Node,
    Recipe,
    ScorecardThreshold,
)
from studio_contracts.scorecard import Aggregate, CaseResult, Gate, GateThreshold, Judge, Scorecard
from studio_contracts.trace import Tokens, TraceEvent

SCHEMA_VERSION = "0.2.0-draft"

__all__ = [
    "SCHEMA_VERSION",
    "AgentConfig",
    "Aggregate",
    "CaseResult",
    "cost_of",
    "Dag",
    "Edge",
    "EmbeddingService",
    "Gate",
    "GateThreshold",
    "Judge",
    "KbBinding",
    "KbSearch",
    "KbSearchResultItem",
    "LLM",
    "Node",
    "NodeType",
    "Recipe",
    "Scorecard",
    "ScorecardThreshold",
    "TraceEvent",
    "TraceWriter",
    "Tokens",
]
