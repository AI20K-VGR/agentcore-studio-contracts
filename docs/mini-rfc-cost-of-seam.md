---
id: studio.mini-rfc.cost-of-seam
type: mini-rfc
status: DRAFT — chờ mentor-approval (README: "Đổi contract phải có mentor-approval")
author: AIE-1 — Trần Bá Đạt
date: 2026-08-24
neo: DL-11.A1-5 (engine decision-log) · studio_kb/cost.py:14-24 (#121) · .importlinter
addresses: "agentcore-studio-engine#38 — cost=0.0 tại điểm emit dù tokens đã thật"
---

# Mini-RFC — dời `cost_of()` + bảng đơn giá xuống `studio_contracts`

## Vấn đề
`studio_engine` (`interpreter.py`, `agent_loop.py`) đã tính `tokens` thật tại điểm dựng mỗi
`TraceEvent`, nhưng `cost` luôn hard-code `0.0` — bảng đơn giá (`PROMPT_RATE_PER_1K`,
`COMPLETION_RATE_PER_1K`) và `cost_of()` sống ở `studio_kb`, còn `.importlinter` xếp
`studio_kb`/`studio_engine` là sibling độc lập, cấm import lẫn nhau. Chi tiết đầy đủ:
`agentcore-studio-engine` issue #38.

Đây không phải hướng mới — chính `studio_kb/cost.py:14-24` (DE, gắn #121) đã ghi trước:
*"`cost_of` cuối cùng phải nằm nơi interpreter import được — `contracts`"*, chỉ chưa ai làm.

## Đề xuất
Thêm `studio_contracts.cost` (module MỚI, không đụng field/model nào đã có):
- `PROMPT_RATE_PER_1K`, `COMPLETION_RATE_PER_1K` — copy nguyên giá trị từ `studio_kb.cost`.
- `cost_of(tokens: Tokens) -> float` — copy nguyên logic + làm tròn 6 chữ số.
- Re-export qua `studio_contracts.__init__` (`from studio_contracts import cost_of`).

`studio_kb.cost` đổi từ **định nghĩa** sang **import lại** 3 tên trên từ `studio_contracts.cost`
— zero đổi hành vi cho `price_mismatches`/`aggregate_run_cost`/`PgCostReader`, vẫn gọi đúng tên cũ.

`studio_engine` gọi `cost_of(tokens)` ngay tại dòng dựng `TraceEvent` (5 điểm emit:
`interpreter.py` 1 điểm, `agent_loop.py` 4 điểm) thay vì `cost=0.0`/`cost=_NO_COST`.

## Vì sao là additive, không phải breaking
Không sửa/xoá field nào trên `Tokens`/`TraceEvent` hay bất kỳ pydantic model nào —
`tests/test_freeze_guard.py` chỉ gate model field, đã đọc để xác nhận. `SCHEMA_VERSION` không
cần bump. Rủi ro duy nhất là *drift* nếu sau này ai đó định nghĩa lại `cost_of` ở nơi thứ 2 — lưới
đã có sẵn: `studio_kb.price_mismatches()` bắt đúng ca đó.

## Cần ký
Mentor-approval theo README (mọi domain ăn theo contracts). Không cần 4/4 chữ ký kiểu
umbrella-contract §3 vì đây không phải freeze — SCHEMA_VERSION còn "0.2.0-draft".
