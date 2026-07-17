"""kb.search contract (R-SPEC A1#3, umbrella-contract.md:138-144) — bút DE.

Permission filter is enforced AT RETRIEVAL (INV-1/DEC-E9), fail-closed;
`section_roles` resolves server-side (a client-declared value is ignored —
this is what stops T6 label-spoof). A chunk that doesn't match scope must
NEVER leave this function — filtering "after the fact" via the LLM is a
forbidden anti-pattern. Owner: DE bút; AIE-1 consumes this in the
`kb-retrieve` node executor.

`KbSearch` is an interface only (P5 implements it) — no method body /
NotImplementedError here.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict


class KbSearchResultItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str
    text: str
    score: float
    tenant: str
    section_role: str


@runtime_checkable
class KbSearch(Protocol):
    """kb.search seam — implementation lands at P5 (DE)."""

    async def search(
        self,
        query: str,
        tenant: str,
        section_roles: list[str],
        top_k: int,
    ) -> list[KbSearchResultItem]: ...
