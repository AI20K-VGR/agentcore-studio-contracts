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
