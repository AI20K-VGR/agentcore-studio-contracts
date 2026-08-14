"""Freeze-guard discipline (phase-2 v0-draft, Decision #7 — NOT frozen for
real yet, but the `frozen=True` mechanics must already work so the switch to
real freeze later is a no-op):

1. Every contract model is pydantic `frozen=True` — mutating an instance
   after construction must raise, not silently succeed.
2. Additive-only: adding a REQUIRED field is a breaking change (an old payload
   fails validation) — this is the mechanical signal that a required-add
   needs a DEC + SCHEMA_VERSION bump, unlike an OPTIONAL add (see
   test_roundtrip.py::test_additive_optional_field_does_not_break_old_roundtrip).
"""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError
from studio_contracts import KbSearchResultItem
from studio_contracts.recipe import ScorecardThreshold
from studio_contracts.scorecard import GateThreshold

ANKOR_ID = UUID("a0000000-0000-0000-0000-000000000001")


def test_frozen_rejects_mutation() -> None:
    item = KbSearchResultItem(
        chunk_id="chunk-1",
        text="t",
        score=0.5,
        tenant_id=ANKOR_ID,
        section_role="public",
    )
    with pytest.raises(ValidationError):
        item.chunk_id = "chunk-2"  # type: ignore[misc]


def test_required_add_breaks_old_payload() -> None:
    old_payload = {
        "chunk_id": "chunk-1",
        "text": "t",
        "score": 0.5,
        "tenant_id": str(ANKOR_ID),
        "section_role": "public",
    }

    class KbSearchResultItemWithRequiredAdd(BaseModel):
        model_config = ConfigDict(frozen=True)

        chunk_id: str
        text: str
        score: float
        tenant_id: UUID
        section_role: str
        new_required_field: str  # simulated breaking required-add

    with pytest.raises(ValidationError):
        KbSearchResultItemWithRequiredAdd.model_validate(old_payload)


def test_tenant_id_rejects_non_uuid() -> None:
    """D-13 / DEC-B: tenant_id is a strict UUID — a slug like "ankor" (the old
    wire value) must now be REJECTED, proving identity is the immutable id and
    not a human-collidable name."""
    with pytest.raises(ValidationError):
        KbSearchResultItem(
            chunk_id="chunk-1",
            text="t",
            score=0.5,
            tenant_id="ankor",
            section_role="public",
        )


def test_gate_threshold_rejects_out_of_range() -> None:
    """`GateThreshold` là ô ghi lại ngưỡng đã dùng để ra `verdict`. Một ngưỡng
    ngoài `[0, 1]` không phải "ngưỡng khắt khe" hay "ngưỡng lỏng" — nó là một
    ngưỡng VÔ NGHĨA, và `success_rate >= -999` đúng với mọi agent, kể cả agent
    hỏng toàn tập. Đo trước khi vá (`compute_scorecard` với 3/3 case
    `success=False`, `citation_accuracy=0.0`): ngưỡng `(-999, -999)` cho
    `verdict="PASS"`, cùng dữ liệu với ngưỡng `(0.9, 0.95)` cho `FAIL`.

    Ràng buộc đặt ở contract chứ không ở `compute.py`: mọi caller đều đi qua
    đây, kể cả caller không qua route (script, `EvalHarness.run` gọi thẳng,
    producer sau này). Xem `kit#129` (thẩm định VinSOC, vấn đề A) — bản sinh
    đôi ở `ScorecardThreshold` (`recipe.py`, bút SWE) là §7 mục 1, KHÔNG sửa
    trong PR này để giữ đúng lane."""
    for success, citation in ((-999.0, -999.0), (-0.01, 0.5), (0.5, 1.01), (2.0, 0.5)):
        with pytest.raises(ValidationError):
            GateThreshold(success=success, citation_accuracy=citation)


def test_gate_threshold_accepts_boundaries() -> None:
    """Bất đối xứng có chủ đích với bài trên: `0.0` và `1.0` là ngưỡng HỢP LỆ
    (chấp mọi thứ / đòi tuyệt đối), không được siết nhầm thành `gt/lt`. Bài này
    là thứ giết mutant `ge→gt` và `le→lt`."""
    for success, citation in ((0.0, 0.0), (1.0, 1.0), (0.9, 0.95)):
        assert GateThreshold(success=success, citation_accuracy=citation).success == success


def test_scorecard_threshold_rejects_out_of_range() -> None:
    """`ScorecardThreshold` là ngưỡng CLIENT khai lúc dựng recipe (`kit#129` §3.1, vấn đề A —
    bản sinh đôi của `test_gate_threshold_rejects_out_of_range` ở trên, khác model, khác chủ).
    Trước bản vá: `apps/studio/routes/runs.py` nhận thẳng `success_threshold`/
    `citation_accuracy_threshold` từ request body, không kiểm gì — `-999` được chấp nhận, MỌI
    agent qua `POST /api/runs`/`/evaluate`/`/publish` đều "đạt" bất kể chất lượng thật."""
    for success, citation in ((-999.0, -999.0), (-0.01, 0.5), (0.5, 1.01), (2.0, 0.5)):
        with pytest.raises(ValidationError):
            ScorecardThreshold(success=success, citation_accuracy=citation)


def test_scorecard_threshold_accepts_boundaries() -> None:
    """Bất đối xứng có chủ đích, cùng lý do `test_gate_threshold_accepts_boundaries`: `0.0`/`1.0`
    hợp lệ, giết mutant `ge→gt`/`le→lt`."""
    for success, citation in ((0.0, 0.0), (1.0, 1.0), (0.9, 0.95)):
        assert ScorecardThreshold(success=success, citation_accuracy=citation).success == success
