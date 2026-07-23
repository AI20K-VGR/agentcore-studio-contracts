# agentcore-studio-contracts

> Frozen pydantic contracts (recipe / trace-event / kb.search / scorecard) — layer ĐÁY, mọi domain phụ thuộc.

**Owner:** mentor/shared (đổi cần mentor duyệt) · **Loại:** uv workspace member (Python 3.14) · **Repo cha:** [agentcore-studio-kit](https://github.com/AI20K-VGR/agentcore-studio-kit)

## Repo này là gì
Submodule `packages/contracts` của workspace `agentcore-studio-kit`. Đây là **nền chung**: mọi domain (kb/engine/workbench/evalhub/app) import contracts. Đổi ở đây ảnh hưởng **tất cả** → mọi PR cần **mentor-approval**.

## ⚠️ Test chạy trong workspace
Contracts là layer đáy (không phụ thuộc domain nào) nhưng test round-trip + freeze-guard nên chạy trong workspace để chắc khớp với các domain tiêu thụ:
- **Làm việc qua repo cha:** `git clone --recursive git@github.com:AI20K-VGR/agentcore-studio-kit.git`, rồi `cd packages/contracts` để sửa / commit / push chính repo này.
- **Test đầy đủ:** đẩy PR → CI tự **dựng lại full workspace** rồi chạy `pytest packages/contracts/tests` (Phương án B).

## CI
`.github/workflows/ci.yml` chỉ là **stub** gọi reusable workflow chung ở repo cha:
`AI20K-VGR/agentcore-studio-kit/.github/workflows/reusable-domain-ci.yml@main`.
Muốn đổi quy trình CI thì sửa ở repo cha (1 chỗ).

## Quy tắc
- SCHEMA_VERSION **chỉ additive** — không xoá/đổi field cũ (freeze-guard chặn).
- Đổi contract phải có mentor-approval vì mọi domain ăn theo.
- Không commit tài liệu mentor/rubric/answer-key (pre-commit `nda-denylist` chặn).

📖 Phân quyền + luồng thao tác đầy đủ: [GITFLOWS.md](https://github.com/AI20K-VGR/agentcore-studio-kit/blob/main/GITFLOWS.md)
