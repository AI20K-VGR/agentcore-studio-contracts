"""Round-trip tests for the 4 v0-draft contracts (Recipe/TraceEvent/
KbSearchResultItem/Scorecard) — the contract IS this test (R-SPEC A1, phase-2).

F12 — Edge's `from` alias must survive serialize -> deserialize in BOTH
directions (by_alias=True dump/validate AND by-name dump/validate). A
round-trip test that only checks one direction is a false-green: it would
still pass even if `populate_by_name=True` were missing, because `by_alias`
dumps always use "from" and Edge's alias validates "from" regardless. Only
the by-name direction proves `populate_by_name=True` actually works.
"""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError
from studio_contracts import (
    AgentConfig,
    Aggregate,
    CaseResult,
    Dag,
    Edge,
    Gate,
    GateThreshold,
    Judge,
    KbBinding,
    KbSearchResultItem,
    Node,
    NodeType,
    Recipe,
    Scorecard,
    ScorecardThreshold,
    TraceEvent,
)
from studio_contracts.trace import Tokens

# Immutable tenant UUID (D-13) standing in for the human name "ankor".
ANKOR_ID = UUID("a0000000-0000-0000-0000-000000000001")


def _sample_recipe() -> Recipe:
    return Recipe(
        agent_id="agent-1",
        tenant_id=ANKOR_ID,
        agent_config=AgentConfig(
            instructions="Answer from KB only.",
            model="gpt-4o-mini",
            tool_whitelist=["kb_search"],
        ),
        dag=Dag(
            nodes=[
                Node(id="n1", type=NodeType.KB_RETRIEVE, params={}),
                Node(id="n2", type=NodeType.LLM_STEP, params={"temp": 0.0}),
            ],
            edges=[Edge(from_="n1", to="n2", when=None)],
        ),
        kb_binding=KbBinding(kb_id="kb-1", scope="ankor/public"),
        golden_set_ref="golden-set-1",
        scorecard_threshold=ScorecardThreshold(success=0.9, citation_accuracy=0.95),
    )


def _sample_trace_event() -> TraceEvent:
    return TraceEvent(
        event_id="evt-1",
        run_id="run-1",
        agent_id="agent-1",
        tenant_id=ANKOR_ID,
        node_id="n1",
        node_type=NodeType.KB_RETRIEVE,
        ts="2026-07-17T00:00:00Z",
        inputs_hash="hash-1",
        outputs={"answer": "ok"},
        tokens=Tokens(prompt=10, completion=20),
        cost=0.001,
        citations=["chunk-1"],
    )


def _sample_kb_result() -> KbSearchResultItem:
    return KbSearchResultItem(
        chunk_id="chunk-1",
        text="Some retrieved text.",
        score=0.87,
        tenant_id=ANKOR_ID,
        section_role="public",
    )


def _sample_scorecard() -> Scorecard:
    return Scorecard(
        agent_id="agent-1",
        golden_set_ref="golden-set-1",
        results=[
            CaseResult(
                case_id="case-1",
                expected="A",
                actual="A",
                success=True,
                citation_accuracy=1.0,
                judge=Judge(label="pass", agreement=0.95),
            )
        ],
        aggregate=Aggregate(success_rate=1.0, citation_accuracy=1.0),
        gate=Gate(
            threshold=GateThreshold(success=0.9, citation_accuracy=0.9),
            verdict="PASS",
        ),
    )


def _assert_roundtrip_both_directions(original: BaseModel) -> None:
    model_cls = type(original)

    by_alias = original.model_dump(mode="json", by_alias=True)
    restored_by_alias = model_cls.model_validate(by_alias)
    assert restored_by_alias == original
    assert restored_by_alias.model_dump(mode="json", by_alias=True) == by_alias

    by_name = original.model_dump(mode="json", by_alias=False)
    restored_by_name = model_cls.model_validate(by_name)
    assert restored_by_name == original
    assert restored_by_name.model_dump(mode="json", by_alias=False) == by_name


def test_recipe_roundtrip_both_directions() -> None:
    _assert_roundtrip_both_directions(_sample_recipe())


def test_trace_event_roundtrip_both_directions() -> None:
    _assert_roundtrip_both_directions(_sample_trace_event())


def test_kb_search_result_roundtrip_both_directions() -> None:
    _assert_roundtrip_both_directions(_sample_kb_result())


def test_scorecard_roundtrip_both_directions() -> None:
    _assert_roundtrip_both_directions(_sample_scorecard())


def test_edge_accepts_alias_and_name() -> None:
    """populate_by_name=True must accept BOTH the alias `from` and the field
    name `from_` when building an Edge directly from a dict.
    """
    via_alias = Edge.model_validate({"from": "a", "to": "b"})
    via_name = Edge.model_validate({"from_": "a", "to": "b"})
    assert via_alias == via_name == Edge(from_="a", to="b")


def test_nodetype_closed_rejects_7th() -> None:
    with pytest.raises(ValueError):
        NodeType("not-a-real-node-type")

    with pytest.raises(ValidationError):
        Node.model_validate({"id": "n1", "type": "not-a-real-node-type", "params": {}})


def test_schema_version_present_and_format() -> None:
    from studio_contracts import SCHEMA_VERSION

    assert isinstance(SCHEMA_VERSION, str)
    assert SCHEMA_VERSION == "0.2.0-draft"


def test_additive_optional_field_does_not_break_old_roundtrip() -> None:
    """Additive-only smoke: an OPTIONAL field added to a contract must not
    break validating an old payload that predates the field (forward-compat).
    A REQUIRED add is the breaking counter-case, covered by
    test_freeze_guard.py::test_required_add_breaks_old_payload.
    """

    old_payload = _sample_kb_result().model_dump(mode="json")

    class KbSearchResultItemV2(BaseModel):
        model_config = ConfigDict(frozen=True)

        chunk_id: str
        text: str
        score: float
        tenant_id: UUID
        section_role: str
        new_optional_field: str | None = None

    restored = KbSearchResultItemV2.model_validate(old_payload)
    assert restored.new_optional_field is None


def test_scorecard_recipe_hash_optional_old_payload_still_validates() -> None:
    """D11 (ruling D-24, `02-MATRIX.md:284`) — `Scorecard.recipe_hash` is
    additive-OPTIONAL, so a pre-D11 `Scorecard` payload (no `recipe_hash` key
    at all) must still validate, and read back as `None`.

    This is the direction that proves "not breaking": old producer -> new
    schema. The breaking counter-direction (required-add) is pinned in
    test_freeze_guard.py::test_required_add_breaks_old_payload. Together they
    are why this change does NOT bump `SCHEMA_VERSION`.

    `None` is not a benign default: publish MUST read it as "cannot verify
    which recipe this scorecard certifies => REFUSE" (fail-closed). The safety
    lives in the consumer, which is exactly why OPTIONAL is sufficient here.
    """
    old_payload = _sample_scorecard().model_dump(mode="json")
    del old_payload["recipe_hash"]
    assert "recipe_hash" not in old_payload

    restored = Scorecard.model_validate(old_payload)

    assert restored.recipe_hash is None
    _assert_roundtrip_both_directions(restored)

    # ...and a producer that DOES supply it round-trips unchanged.
    with_hash = _sample_scorecard().model_copy(update={"recipe_hash": "sha256:deadbeef"})
    assert with_hash.recipe_hash == "sha256:deadbeef"
    _assert_roundtrip_both_directions(with_hash)
