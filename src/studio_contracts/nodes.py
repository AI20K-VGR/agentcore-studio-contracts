"""Closed-set node-type enum — the SOLE source of truth (R-SPEC A2,
umbrella-contract.md:62-73).

Workbench graph-lint and engine executor both import `NodeType` from here so
the closed 6-value set never drifts between the two consumers. Adding a 7th
value is a breaking change (cap cứng — CẤM thêm node ngoài 6 loại, CẤM DSL
turing-complete). A change here requires a mini-RFC + 4/4 owner sign-off per
umbrella-contract.md §3 (recipe schema owner: SWE).
"""

from __future__ import annotations

from enum import StrEnum


class NodeType(StrEnum):
    """The 6 closed node types for the AgentCore Studio DAG interpreter."""

    KB_RETRIEVE = "kb-retrieve"
    LLM_STEP = "llm-step"
    CONDITION = "condition"
    TOOL_CALL = "tool-call"
    HITL_PAUSE = "hitl-pause"
    END = "end"
