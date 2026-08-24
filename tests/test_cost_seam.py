"""`cost_of` — the price seam moved here from `studio_kb.cost` (engine#38) so `studio_engine`
can reach it directly at emit time despite `.importlinter` forbidding `studio_engine` ->
`studio_kb`. `studio_kb.cost` re-exports these same names — see its module docstring.
"""

from __future__ import annotations

from studio_contracts import cost_of
from studio_contracts.cost import COMPLETION_RATE_PER_1K, PROMPT_RATE_PER_1K
from studio_contracts.trace import Tokens


def test_cost_of_tat_dinh_va_dung_don_gia() -> None:
    """`cost_of` = prompt/1k·PROMPT_RATE + completion/1k·COMPLETION_RATE, làm tròn 6 chữ số. Tokens=0 → 0."""
    assert cost_of(Tokens(prompt=0, completion=0)) == 0.0
    assert cost_of(Tokens(prompt=1000, completion=0)) == PROMPT_RATE_PER_1K
    assert cost_of(Tokens(prompt=1000, completion=1000)) == PROMPT_RATE_PER_1K + COMPLETION_RATE_PER_1K
    assert cost_of(Tokens(prompt=137, completion=42)) == round(
        137 / 1000 * PROMPT_RATE_PER_1K + 42 / 1000 * COMPLETION_RATE_PER_1K, 6
    )


def test_cost_of_reachable_from_package_root() -> None:
    """`from studio_contracts import cost_of` must work — this is the exact import
    `studio_engine.interpreter` / `studio_engine.agent_loop` use at their emit sites."""
    assert cost_of(Tokens(prompt=1000, completion=1000)) == 0.018
