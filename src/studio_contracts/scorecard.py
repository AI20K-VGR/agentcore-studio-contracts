"""Scorecard contract (R-SPEC A1#4, umbrella-contract.md:146-158) — bút AIE-2.

Owner: AIE-2 bút + cấp verdict; SWE only wires the publish/rollback gate to
read `gate.verdict` (SWE does not own scorecard render). `gate.verdict == "FAIL"`
is a hard gate for Publish (INV-6) — never advisory-only.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Judge(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    agreement: float


# Vì sao `outcome` là một tập ĐÓNG chứ không phải chuỗi tự do: nó điều khiển cách giao diện gom
# nhóm và tô màu, nên một giá trị lạ sẽ lặng lẽ rơi khỏi mọi nhóm thay vì báo lỗi.
#
#   pass_answer       nhánh trả lời — câu trả lời chứa cụm kỳ vọng
#   pass_refusal      nhánh hàng rào — agent từ chối, không trích gì ngoài phạm vi
#   fail_leak         HÀNG RÀO BỊ THỦNG — trả lời câu đáng lẽ từ chối, hoặc trích chunk ngoài phạm vi
#   fail_unobserved   nhánh hàng rào — từ chối đúng, nhưng không có event `kb-retrieve` để xác minh
#   fail_refused      nhánh trả lời — agent từ chối một câu đáng lẽ trả lời được
#   fail_wrong_answer nhánh trả lời — có trả lời nhưng không chứa cụm kỳ vọng
#   unknown           Scorecard ghi trước khi có trường này
#
# `fail_leak` và `fail_unobserved` cùng cho `success=False` nhưng khác nhau về CHẤT: cái đầu là sự
# cố bảo mật, cái sau là thiếu dữ liệu quan trắc. Gộp hai cái đó lại là bỏ mất thông tin duy nhất
# khiến bảng điểm dùng được để quyết định.
CaseOutcome = Literal[
    "pass_answer",
    "pass_refusal",
    "fail_leak",
    "fail_unobserved",
    "fail_refused",
    "fail_wrong_answer",
    "unknown",
]


class CaseResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str
    expected: str
    actual: str
    success: bool
    citation_accuracy: float
    expects_refusal: bool = False
    """Case này thuộc nhánh **hàng rào** (agent phải từ chối) hay nhánh **trả lời**.

    Hai nhánh chấm bằng hai luật khác nhau, nên gộp chúng vào một `success_rate` duy nhất là bỏ mất
    thứ người đọc cần biết nhất: *thất bại ở đây là agent trả lời sai, hay là hàng rào bị thủng?*
    Hai kết luận đó dẫn tới hai việc phải làm hoàn toàn khác nhau.

    KHÔNG suy được từ các trường khác: `citation_accuracy == 1.0` là quy ước vacuous-truth của nhánh
    từ-chối, nhưng nhánh trả-lời có `expected_citation` rỗng **cũng** cho `1.0`."""

    outcome: CaseOutcome = "unknown"
    """VÌ SAO case này đạt hoặc trượt — không chỉ đạt/trượt.

    `success: bool` nói *có*, trường này nói *tại sao*. Khác biệt quan trọng nhất nằm ở nhánh hàng
    rào: `fail_leak` (agent trả lời câu đáng lẽ phải từ chối — **rò rỉ thật**) và `fail_unobserved`
    (agent từ chối đúng, nhưng không quan sát được lượt tra KB nên chấm fail-closed) cùng ra
    `success=False`, trong khi cái đầu là sự cố bảo mật còn cái sau là thiếu dữ liệu quan trắc.
    Không phân biệt được hai ca đó thì bảng điểm không dùng để quyết định gì được.

    Mặc định `"unknown"` để mọi Scorecard đã ghi trước khi có trường này vẫn đọc lại được — cùng
    lý do `judge` là optional (D11, Q1)."""

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

    n_scored_citation: int | None = Field(default=None, ge=0)
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

    @model_validator(mode="after")
    def _rate_and_denominator_must_agree(self) -> Aggregate:
        """A rate and its denominator must tell the same story.

        Two symmetric lies, each a different way of misreporting one division:

        - `citation_accuracy is None` (never measured) while claiming a
          non-empty denominator — the axis cannot be both unmeasured and
          measured over 25 cases.
        - a real rate while claiming an empty denominator — a number divided by
          nothing.

        `n_scored_citation is None` stays legal with any rate: the absence of a
        count contradicts nothing, it is simply not carried (see the field
        docstring). Only a denominator that IS present can disagree.

        **This rejects nothing that used to validate.** Both forbidden states
        need `citation_accuracy = None` or `n_scored_citation = 0`, and neither
        was representable before this change — the field did not exist and the
        rate was a plain `float`. The constraint fences off newly reachable
        states, so it is not a breaking tightening of an existing shape."""
        if self.n_scored_citation is None:
            return self
        if self.citation_accuracy is None and self.n_scored_citation > 0:
            raise ValueError(
                f"citation_accuracy=None (trục chưa đo) nhưng n_scored_citation="
                f"{self.n_scored_citation} — mẫu số > 0 nghĩa là ĐÃ đo. Mẫu số rỗng phải là 0."
            )
        if self.citation_accuracy is not None and self.n_scored_citation == 0:
            raise ValueError(
                f"citation_accuracy={self.citation_accuracy} nhưng n_scored_citation=0 — "
                "một tỷ lệ chia cho không. Mẫu số rỗng ⇒ citation_accuracy phải là None."
            )
        return self


class GateThreshold(BaseModel):
    """Ngưỡng đã dùng để ra `verdict`, ghi lại cùng verdict.

    `ge=0.0, le=1.0`: cả hai vế so sánh ở `compute_scorecard` là tỷ lệ trong
    `[0, 1]`, nên một ngưỡng ngoài khoảng không phải "khắt khe" hay "lỏng" —
    nó vô nghĩa, và `success_rate >= -999` đúng với mọi agent kể cả agent hỏng
    toàn tập. Biên `0.0`/`1.0` VẪN hợp lệ (chấp mọi thứ / đòi tuyệt đối) nên
    là `ge/le`, không phải `gt/lt`.

    Đặt ở contract chứ không ở `compute.py` vì mọi caller đều đi qua đây, kể
    cả caller không qua route. Bản sinh đôi `ScorecardThreshold` (`recipe.py`,
    bút SWE) là việc riêng — xem `kit#129` §7 mục 1.
    """

    model_config = ConfigDict(frozen=True)

    success: float = Field(ge=0.0, le=1.0)
    citation_accuracy: float = Field(ge=0.0, le=1.0)


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

    @model_validator(mode="after")
    def _unmeasured_axis_cannot_pass(self) -> Scorecard:
        """An axis that was never measured MUST NOT carry `verdict = "PASS"`.

        `DEC-D16-03` states this, and `INV-6` makes `verdict` a hard cut for
        Publish rather than advice — so *"not estimable"* reaching a consumer as
        PASS is the failure mode with real blast radius, not a cosmetic one.

        **Why it lives on `Scorecard` and not on `Aggregate`.** The invariant
        spans two frozen models: the measurement is in `aggregate`, the decision
        is in `gate`. Neither can see the other, which is exactly how a scorecard
        reading *"citation was never measured"* next to *"gate PASSED"* was able
        to validate cleanly. `Scorecard` is the first scope that holds both.

        **Deliberately one-directional.** `FAIL` with a measured axis stays
        legal: a run fails for reasons that have nothing to do with this axis
        (`success_rate` below threshold, and later gates). This rejects only the
        combination *unmeasured + PASS* — it does not turn the contract into a
        second place that decides verdicts. `compute_scorecard` remains the only
        thing that DECIDES; this is a floor under the result, not a duplicate of
        the policy.

        **Rejects nothing that used to validate:** `citation_accuracy = None`
        became representable in this same change."""
        if self.aggregate.citation_accuracy is None and self.gate.verdict == "PASS":
            raise ValueError(
                "aggregate.citation_accuracy=None (trục chưa đo được) nhưng gate.verdict='PASS' — "
                "không đo được thì không PASS được (DEC-D16-03; INV-6 coi verdict là cổng cứng)."
            )
        return self

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
