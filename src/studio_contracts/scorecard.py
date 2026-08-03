"""Scorecard contract (R-SPEC A1#4, umbrella-contract.md:146-158) — bút AIE-2.

Owner: AIE-2 bút + cấp verdict; SWE only wires the publish/rollback gate to
read `gate.verdict` (SWE does not own scorecard render). `gate.verdict == "FAIL"`
is a hard gate for Publish (INV-6) — never advisory-only.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class Judge(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    agreement: float


class CaseResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    expected: str
    actual: str
    success: bool
    citation_accuracy: float
    judge: Judge


class Aggregate(BaseModel):
    model_config = ConfigDict(frozen=True)

    success_rate: float
    citation_accuracy: float


class GateThreshold(BaseModel):
    model_config = ConfigDict(frozen=True)

    success: float
    citation_accuracy: float


class Gate(BaseModel):
    model_config = ConfigDict(frozen=True)

    threshold: GateThreshold
    verdict: Literal["PASS", "FAIL"]


class Scorecard(BaseModel):
    """Scorecard schema — bút AIE-2. `results` come from the 30-case golden
    set (from doc-factory DE); `gate.verdict` is the hard cut for Publish.
    """

    model_config = ConfigDict(frozen=True)

    agent_id: str
    golden_set_ref: str
    results: list[CaseResult]
    aggregate: Aggregate
    gate: Gate
    recipe_hash: str | None = None
    """Hash of the EXACT recipe revision this scorecard was produced from.

    Answers the only question that makes a stored verdict trustworthy later:
    *"which recipe does this PASS actually certify?"* Without it, a scorecard
    and a recipe can drift apart silently and `gate.verdict` becomes a claim
    about nothing in particular.

    **Consumer rule — fail-closed.** Publish MUST treat `recipe_hash is None`
    as *"cannot verify which recipe this certifies ⇒ REFUSE"*, never as
    *"probably fine"*. Because the safety lives in the consumer, an OPTIONAL
    field is sufficient here — a required-add would be a breaking change
    (`__init__.py:5-12`) for zero extra safety.

    D11 (ruling D-24, `docs/requirements/00-orientation/02-MATRIX.md:284`:
    *"Fix the schemas before Day 20, then write the tests. Add `recipe_hash`
    to `Scorecard`"*, owner AIE-2). Landed as additive-optional, so no
    `SCHEMA_VERSION` bump.

    **Known gap, stated rather than hidden:** this field currently has NO
    producer. `Recipe` has no `version`/hash field (`recipe.py:79-94`) even
    though `wb.recipe_versions` already exists
    (`studio_workbench/schema.py:39`). How the value is derived is a joint
    decision with SWE (pen of `Recipe`) — tracked in
    `agentcore-studio-kit/docs/decisions/scorecard.md` as `DEC-03`, owner SWE,
    due D12. Until a producer exists every real `Scorecard` carries `None`,
    and the fail-closed rule above is what keeps that honest."""
