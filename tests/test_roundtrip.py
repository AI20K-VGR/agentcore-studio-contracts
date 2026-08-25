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
            system_prompt="Answer from KB only.",
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


def test_agent_config_reads_old_published_instructions_shape() -> None:
    """A recipe published BEFORE the `instructions` -> `system_prompt` rename
    (contracts#14) has `agent_config.instructions` in the DB (`wb.recipes`/
    `wb.recipe_versions`, `jsonb`, never rewritten in place). `system_prompt`
    carries `Field(validation_alias=AliasChoices("system_prompt", "instructions"))`
    specifically so this old shape still validates — without it, every
    already-published agent loses `/chat`
    (`apps/studio/routes/chat.py::_load_published_recipe`) and `GET` recipe
    (`routes/agents.py`).
    """
    old_shape_agent_config = {
        "instructions": "Answer from KB only.",
        "model": "gpt-4o-mini",
        "tool_whitelist": ["kb_search"],
    }

    restored = AgentConfig.model_validate(old_shape_agent_config)

    assert restored.system_prompt == "Answer from KB only."
    # New producers may build with either name; both must agree with the old row.
    assert restored == AgentConfig(
        system_prompt="Answer from KB only.",
        model="gpt-4o-mini",
        tool_whitelist=["kb_search"],
    )


def test_agent_config_serializes_only_the_new_name() -> None:
    """contracts#14 review round 2: a plain `Field(alias="instructions")` sets
    BOTH the validation alias AND the serialization alias in pydantic v2, so
    `model_dump(by_alias=True)` kept emitting "instructions" forever — the
    rename never actually reached the wire (API responses, `wb.recipes`
    writes), even for brand-new recipes published after the rename landed.
    `validation_alias=AliasChoices(...)` (no plain `alias=`) is what actually
    fixes this: read either old-or-new-shape input, but always WRITE the new
    name. This is the test that would have caught the round-2 finding.
    """
    config = AgentConfig(system_prompt="Answer from KB only.", model="gpt-4o-mini", tool_whitelist=["kb_search"])

    dumped = config.model_dump(mode="json", by_alias=True)

    assert "system_prompt" in dumped
    assert "instructions" not in dumped


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
    assert SCHEMA_VERSION == "0.3.0-draft"


def test_case_result_judge_none_for_unjudged_case() -> None:
    """D11 (Q1, evalhub docs/scorecard-v0.md §3): `CaseResult.judge` must
    accept `None` for exact-match/refusal cases (no LLM-judge ran) — this is
    the ONLY honest value pre-S3, since a placeholder `Judge(...)` would be
    indistinguishable from a real 100%-agreement judge run downstream."""
    result = CaseResult(
        case_id="case-1",
        expected="A",
        actual="A",
        success=True,
        citation_accuracy=1.0,
        judge=None,
    )
    assert result.judge is None
    _assert_roundtrip_both_directions(result)


def test_case_result_with_real_judge_still_works() -> None:
    """Loosening `judge` to optional must not affect a producer that DOES
    pass a real `Judge` (old caller / S3 LLM-judge case) — same object as
    before this change, unaffected."""
    result = CaseResult(
        case_id="case-1",
        expected="A",
        actual="A",
        success=True,
        citation_accuracy=1.0,
        judge=Judge(label="pass", agreement=0.95),
    )
    assert result.judge == Judge(label="pass", agreement=0.95)


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


# ── Aggregate trục citation — shape mới (DEC-D16-03), review AIE-1 trên contracts#5 ──────────────
#
# Vì sao ba bài này sống ở ĐÂY chứ không chỉ ở evalhub: `reusable-domain-ci.yml:100` chỉ chạy
# `pytest <domain_path>/tests`, nên CI của repo này KHÔNG bao giờ chạy test của consumer. Không có ba
# bài dưới thì CI xanh ở đây chỉ chứng minh **usage cũ vẫn validate** — không chứng minh shape mới
# hoạt động, và bằng chứng đó nằm hết ở một PR chưa merge của repo khác.


def _scorecard(*, citation_accuracy: float | None, n_scored: int | None, verdict: str) -> Scorecard:
    return Scorecard(
        agent_id="a",
        golden_set_ref="g",
        results=[CaseResult(case_id="C-1", expected="x", actual="x", success=True, citation_accuracy=1.0)],
        aggregate=Aggregate(success_rate=1.0, citation_accuracy=citation_accuracy, n_scored_citation=n_scored),
        gate=Gate(threshold=GateThreshold(success=0.9, citation_accuracy=0.95), verdict=verdict),
    )


def test_truc_chua_do_duoc_khong_the_mang_verdict_PASS() -> None:
    """`citation_accuracy is None` (trục chưa đo) + `verdict = "PASS"` ⇒ `ValidationError`.

    Đây là bất biến mà cả `DEC-D16-03` lẫn docstring của field đều KHAI, và trước bài này không gì
    cưỡng chế nó: hai model `Aggregate`/`Gate` tách rời, không validator nào bắc qua. Một scorecard
    *"trục citation chưa từng đo, nhưng gate PASS"* validate sạch — đúng lớp **vacuous PASS** mà việc
    nới `float | None` sinh ra để đóng, chỉ dời từ *"số sai"* sang *"số đúng, không có lưới"*.

    Ràng buộc này KHÔNG loại payload cũ nào: trước khi nới kiểu, `citation_accuracy = None` **không
    biểu diễn được** (`float`), nên trạng thái bị cấm ở đây chưa từng hợp lệ."""
    with pytest.raises(ValidationError):
        _scorecard(citation_accuracy=None, n_scored=0, verdict="PASS")

    # Đối trọng: cùng trạng thái chưa-đo, verdict FAIL ⇒ hợp lệ. Thiếu vế này thì bài trên vẫn xanh
    # với một model cấm `None` bằng mọi giá — tức cấm luôn thứ PR này sinh ra để cho phép.
    assert _scorecard(citation_accuracy=None, n_scored=0, verdict="FAIL").gate.verdict == "FAIL"


def test_mau_so_va_ty_le_phai_ke_cung_mot_cau_chuyen() -> None:
    """`n_scored_citation` và `citation_accuracy` không được mâu thuẫn nhau.

    Hai ca đối xứng, mỗi ca là một cách nói dối khác nhau về cùng một phép chia:

    - `None` + mẫu số `> 0` — *"chưa đo được"* trong khi khai đã chấm 25 case. Đây là ca phản chứng
      AIE-1 dựng ở review contracts#5.
    - số thật + mẫu số `0` — một tỷ lệ chia cho không.

    `n_scored_citation = None` (producer cũ không mang) **vẫn hợp lệ với mọi tỷ lệ**: vắng mặt một
    phép đếm không mâu thuẫn với gì cả, nó chỉ là chưa biết."""
    with pytest.raises(ValidationError):
        _scorecard(citation_accuracy=None, n_scored=25, verdict="FAIL")

    with pytest.raises(ValidationError):
        _scorecard(citation_accuracy=0.85, n_scored=0, verdict="FAIL")

    assert _scorecard(citation_accuracy=0.85, n_scored=None, verdict="FAIL").aggregate.n_scored_citation is None


def test_mau_so_am_bi_tu_choi() -> None:
    """`n_scored_citation` là một phép đếm ⇒ không âm. Producer duy nhất hôm nay tính bằng `len()`
    nên không sinh được số âm, nhưng kiểu `int | None` một mình không nói ra điều đó — và contract
    là chỗ nói ra, không phải chỗ tin producer."""
    with pytest.raises(ValidationError):
        _scorecard(citation_accuracy=0.85, n_scored=-1, verdict="FAIL")
