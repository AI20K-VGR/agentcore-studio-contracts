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
    judge: Judge | None = None
    """`None` when this case was scored WITHOUT an LLM-judge (exact-match /
    refusal cases — the only kind that exist pre-S3). This must stay `None`
    rather than a constant placeholder `Judge(...)`: `judge.py` requires every
    `Judge.agreement` to be a real agreement score against a hand label
    (R-SPEC A7) — a placeholder value would be indistinguishable from a real
    100%-agreement judge run and silently corrupt any later aggregate over
    `agreement` (INV-4 agreement-check). `Judge` stays required-shaped
    (label + agreement) for the S3 case where a real judge DID run.

    D11 decision (Q1, evalhub `docs/scorecard-v0.md` §3): loosening an
    existing required field to optional is backward-compatible for every
    existing producer (anyone already passing a real `Judge` is unaffected),
    so this is additive, not a SCHEMA_VERSION-bump-worthy break."""


class Aggregate(BaseModel):
    model_config = ConfigDict(frozen=True)

    success_rate: float
    citation_accuracy: float | None
    """Mean citation accuracy over the ANSWER-branch cases only — `None` when
    that denominator does not exist.

    **What question this answers:** *"of the cases where citing something was
    the correct behaviour, how much of the expected evidence did the agent
    actually retrieve?"* Refusal cases are excluded from the denominator by
    `DEC-04`: they carry a pinned `citation_accuracy = 1.0` as a
    **vacuous-truth convention**, not as a measurement, and folding that
    convention into the mean silently inflates the score. Measured cost of
    getting this wrong: a 10-case set reported `0.90` where the true value was
    `0.833`, and `10×1.0 + 20×0.85` lands on exactly `0.90` — i.e. a run that
    should FAIL passes a `0.9` threshold.

    **Consumer rule — `None` is not zero and not "fine".** `None` means the
    denominator was empty (every case was a refusal), so this axis was never
    measured. `DEC-D16-03`: an unmeasured axis MUST NOT produce a PASS —
    `compute_scorecard` emits `gate.verdict = "FAIL"` alongside it. Renderers
    must print something that reads as *not estimable*, never `0.00`: a
    formatted `0.00` is indistinguishable from a real measurement of zero, and
    `0/0` invites the reader to perform a division that does not exist.

    **Why widening to `float | None` is not a `SCHEMA_VERSION` bump.**
    `__init__.py:5-12` lists three breaking shapes (rename · removal ·
    required-add); this is the fourth shape `DEC-01` names — *compatible on the
    wire, NOT compatible with readers*. `DEC-01` allows no bump on the
    condition that zero readers assume non-null. That condition was checked, not
    asserted: one real reader existed
    (`studio_evalhub/render.py` formatting `:.2f`) and it is patched in the same
    change. The condition is met **by fixing the reader**, not by declaring it
    absent.

    The denominator itself travels next to this number as
    `n_scored_citation` — read the two together, never this one alone."""

    n_scored_citation: int | None = None
    """How many cases the `citation_accuracy` mean was actually taken over — the
    denominator, carried explicitly instead of left to the reader to guess.

    **Why a rate alone is malformed evidence.** `citation_accuracy = 0.90` is a
    different claim over 22 cases than over 30, and nothing else on `Scorecard`
    recovers which one it was: `len(results)` counts ALL cases, and the refusal
    cases excluded by `DEC-04` are not marked in a way `Aggregate` can see. A
    consumer reading a rate without its `n` is doing exactly what `kit#134`
    classifies as malformed evidence — reporting a proportion whose sample size
    is unrecoverable.

    **`0` and `None` mean different things, and neither means "fine".**

    - `0`    — the denominator was computed and it was empty (every case was a
               refusal). Pairs with `citation_accuracy = None`; the axis was
               never measured, and `DEC-D16-03` requires `gate.verdict = "FAIL"`
               alongside it. Not estimable is not a PASS.
    - `None` — this producer did not carry the denominator at all (a payload
               written before this field existed). Absence of a count, not a
               count of zero. A consumer MUST NOT read it as `0`, and MUST NOT
               present a rate as trustworthy on the strength of it.

    **Additive-optional, so no `SCHEMA_VERSION` bump.** Unlike the widening on
    `citation_accuracy` above, this is a new OPTIONAL field: every payload
    written before it still validates unchanged, and no reader can have been
    assuming a value that did not exist. This is the plain additive case
    `__init__.py:5-12` allows without a bump — not the fourth shape."""


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
    `agentcore-studio-evalhub/docs/decisions/scorecard.md` as `DEC-03`, owner SWE,
    due D12. Until a producer exists every real `Scorecard` carries `None`,
    and the fail-closed rule above is what keeps that honest."""
