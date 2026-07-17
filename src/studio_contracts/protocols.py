"""EmbeddingService / LLM / TraceWriter seams — interface only.

These are `typing.Protocol` declarations with no method bodies:
`NotImplementedError` bodies belong to the concrete implementations at P4
(LLM/TraceWriter) and P5 (EmbeddingService), never here. Contracts stays the
bottom import-layer (pydantic + stdlib typing only — see .importlinter).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from studio_contracts.trace import TraceEvent


@runtime_checkable
class EmbeddingService(Protocol):
    """R-SPEC A1#5 (umbrella-contract.md:160-165). 2 impl expected: stub local
    fixtures (CI, 100%) + gateway (optional, INV-4 — does not change this
    Protocol). Owner impl: AIE-1.
    """

    async def embed(self, texts: list[str]) -> list[list[float]]: ...


@runtime_checkable
class LLM(Protocol):
    """LLM completion seam consumed by the `llm-step` node executor (AIE-1).
    Implementation lands at P4.
    """

    async def complete(self, prompt: str, **kwargs: object) -> str: ...


@runtime_checkable
class TraceWriter(Protocol):
    """Trace sink seam — owner DE (trace_sink). Implementation lands at P4."""

    async def write(self, event: TraceEvent) -> None: ...
