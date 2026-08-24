"""Recipe contract (R-SPEC A1#1, umbrella-contract.md:99-116) — bút SWE.

v0-draft (Decision #7): NOT frozen-as-in-locked yet — freeze happens when the
owner signs off (mini-RFC + 4/4 signatures). `model_config = ConfigDict(frozen=True)`
below is the pydantic *immutability* mechanic (instances can't be mutated after
construction), which is orthogonal to and precedes the schema-freeze decision.

Additive-only discipline (copy pattern R-DI §4): new OPTIONAL fields may be
added without a SCHEMA_VERSION bump; renames/removals/required-additions are
breaking and need a DEC + bump (see `studio_contracts.SCHEMA_VERSION`).

F12 — `from` is a reserved Python keyword: `Edge.from_` carries `Field(alias="from")`
and `model_config` sets `populate_by_name=True` so callers can build an Edge with
either the field name (`from_=...`) or the wire alias (`from=...`).
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from studio_contracts.nodes import NodeType


class Node(BaseModel):
    """One DAG node — id + closed NodeType + free-form params."""

    model_config = ConfigDict(frozen=True)

    id: str
    type: NodeType
    params: dict[str, object] = Field(default_factory=dict)


class Edge(BaseModel):
    """One DAG edge. `from` is a reserved Python keyword (F12): the field is
    `from_` with wire alias `from`; `populate_by_name=True` accepts either.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    from_: str = Field(alias="from")
    to: str
    when: str | None = None


class Dag(BaseModel):
    """DAG = nodes (∈ 6 closed NodeType) + edges."""

    model_config = ConfigDict(frozen=True)

    nodes: list[Node]
    edges: list[Edge]


class AgentConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    system_prompt: str
    model: str
    tool_whitelist: list[str]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class KbBinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    kb_id: str
    scope: str


class ScorecardThreshold(BaseModel):
    """Ngưỡng client khai lúc dựng recipe (đối lập `GateThreshold` ở `scorecard.py`, bút AIE-2,
    ghi lại ngưỡng đã dùng SAU khi verdict đã ra). VinSOC thẩm định (`kit#129` §3.1, vấn đề A):
    trước bản vá này, `float` trần — client gửi `success_threshold: -999` được server chấp nhận,
    khiến MỌI agent (kể cả agent hỏng toàn tập) "đạt". `ge=0.0, le=1.0`: cả hai vế so sánh ở
    `compute_scorecard` là tỷ lệ trong `[0, 1]`, ngưỡng ngoài khoảng không phải "khắt khe"/"lỏng"
    — nó vô nghĩa. Biên `0.0`/`1.0` VẪN hợp lệ (chấp mọi thứ / đòi tuyệt đối) nên dùng `ge/le`,
    không phải `gt/lt`.

    Quét toàn workspace trước khi vá (không phải đoán): 0 call-site nào dùng giá trị ngoài
    `[0.8, 1.0]` — `contracts/tests`, `engine/scripts+tests`, `workbench/builder.py+tests` đều
    dùng đúng `0.8`/`0.9`/`0.95`. `SCHEMA_VERSION` giữ nguyên (cùng lý do `GateThreshold`,
    `contracts#6`: breaking-by-mechanism nhưng 0 payload thật nào bị chạm).
    """

    model_config = ConfigDict(frozen=True)

    success: float = Field(ge=0.0, le=1.0)
    citation_accuracy: float = Field(ge=0.0, le=1.0)


class Recipe(BaseModel):
    """Recipe schema — bút SWE (R-SPEC A1#1, umbrella-contract.md:99-116).

    graph-lint (SWE, đồng bút): node ∈ 6 loại, không chu trình cấm, edge có
    đích, tool ∈ whitelist; recipe không qua validator = không interpret.
    """

    model_config = ConfigDict(frozen=True)

    agent_id: str
    tenant_id: UUID
    agent_config: AgentConfig
    dag: Dag
    kb_binding: KbBinding
    golden_set_ref: str
    scorecard_threshold: ScorecardThreshold
