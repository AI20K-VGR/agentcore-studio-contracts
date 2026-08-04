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
