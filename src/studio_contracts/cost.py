"""Price seam for `TraceEvent.cost` (engine#38) — the single source of pricing, moved here
from `studio_kb.cost` so `studio_engine` can reach it: `.importlinter`'s layers contract makes
`studio_kb`/`studio_engine` independent siblings, but every quadrant may import `studio_contracts`
(the DIP bottom layer). `studio_kb.cost` now re-exports these names instead of defining them.

`cost` is computed EXACTLY ONCE, at the point each `TraceEvent` is constructed
(`studio_engine.interpreter.run()` / `studio_engine.agent_loop.run_agent_loop()`), right next to
`tokens=tokens`. Every downstream surface (UI test, trace viewer, cost dashboard, `studio_kb`'s
`aggregate_run_cost`) reads the already-computed `event.cost` back — none of them may call
`cost_of` themselves. `studio_kb.price_mismatches()` is the audit gate for that rule: it flags
any `event.cost != cost_of(event.tokens)`, which is exactly what a second computation site
(drift) would produce.
"""

from __future__ import annotations

from studio_contracts.trace import Tokens

# ── Bảng đơn giá (USD / 1000 token) — NGUỒN GIÁ DUY NHẤT ──────────────────────────────────────────
# Giá trị placeholder-deterministic (không mạng/không thời gian): cost-lineage kiểm BẤT BIẾN "một số,
# ba mặt", không kiểm độ chính xác giá thị trường. Đơn giá theo model là honest-TODO: `TraceEvent`
# chưa mang `model`, nên hôm nay một mức phẳng cho mọi node.
PROMPT_RATE_PER_1K = 0.003
COMPLETION_RATE_PER_1K = 0.015


def cost_of(tokens: Tokens) -> float:
    """`tokens → cost` (USD) — nguồn giá duy nhất, áp **một lần tại điểm emit**.

    Tất định: cùng tokens luôn ra cùng số (làm tròn 6 chữ số để tổng cộng dồn không trôi float)."""
    return round(
        tokens.prompt / 1000 * PROMPT_RATE_PER_1K + tokens.completion / 1000 * COMPLETION_RATE_PER_1K,
        6,
    )
