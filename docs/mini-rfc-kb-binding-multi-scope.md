---
id: studio.mini-rfc.kb-binding-multi-scope
type: mini-rfc
status: DRAFT — chờ 4/4 chữ ký (DE · SWE · AIE-1 · AIE-2)
author: AIE-1 — Trần Bá Đạt
date: 2026-08-26
neo: kit#239 (Q1/Q4 đã chốt bằng comment 2026-08-25T17:43Z, AIE-2 không phản đối 2026-08-25T17:52Z) ·
     kit#206 (giữ luật chặn N-node kb-retrieve trên DAG — RFC này KHÔNG đụng luật đó) ·
     GITFLOWS.md §2 (đổi contract = mentor-approval + mini-RFC 4 chữ ký khi rename/required-add)
addresses: "kit#239 Q2 — hình dạng contract cho N knowledge base / 1 agent, mỗi KB một bộ golden"
---

# Mini-RFC — `KbBinding` mang N phạm vi (`section_role`), thay vì 1

## Đã chốt trước RFC này (không mở lại)

- **Q4 = (a)** — "một KB" = một `section_role` (đã có qua `core.sections`, đúng cái tab Tài liệu
  đang hiện). `kb.knowledge_bases` giữ nguyên hiện trạng, không viết.
- **Q1 = (b)** — phạm vi tra cứu thật lúc chạy = `session_context.system_roles ∩ kb_binding scopes`.
  Giao chỉ thu hẹp, không mở rộng; tenant fence (INV-1) không đổi.
- **kit#206** — luật `dag.at_most_one_kb_retrieve_node` (`validator.py:221-228`) giữ nguyên. N
  scope nằm **trong** một `kb_binding`/một node `kb-retrieve`, DAG vẫn tuyến tính.

RFC này chỉ trả lời: **hình dạng field nào** mang N đó, và code nào phải đổi theo.

## Vấn đề — 2 khoảng trống, không phải 1

### 1. Shape số ít (đã nêu trong kit#239)

```python
# packages/contracts/src/studio_contracts/recipe.py
class KbBinding(BaseModel):
    kb_id: str
    scope: str

class Recipe(BaseModel):
    kb_binding: KbBinding    # MỘT, bắt buộc
    golden_set_ref: str      # MỘT, bắt buộc
```

### 2. `kb_binding` hôm nay không phải tham số client — nó bị HARDCODE (chưa nêu trong kit#239)

`packages/workbench/src/studio_workbench/recipe.py:62-96`:

```python
_DEFAULT_KB_ID = "kb-callisto-v1"
_DEFAULT_SCOPE = "ankor/public"
...
kb_bind = KbBinding(kb_id=_DEFAULT_KB_ID, scope=_DEFAULT_SCOPE)
```

`create_recipe()` — hàm builder Form-Feed thật duy nhất còn lại (`create_recipe_d4`, hàm từng
nhận `kb_id`/`scope` làm tham số thật, đã bị xoá 2026-08-24, workbench#41/kit#218) — không nhận
`kb_id`/`scope` từ caller. Nghĩa là **canvas hôm nay không set được KB nào cả**, kể cả 1 cái; mọi
recipe dựng qua `create_recipe`/`recipe_from_canvas` đều gắn cùng 1 demo KB cố định. RFC không chỉ
nới kiểu `str` → `list[str]`, mà còn phải **mở lại đường tham số hoá** đã đóng ở workbench#41.

## Đề xuất shape

```python
class KbBinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    section_role: str          # đổi tên từ `scope` — khớp thẳng Q4=(a), bỏ `kb_id`
                                 # (dư thừa: "1 KB" = section_role, không còn danh tính riêng)

class Recipe(BaseModel):
    ...
    kb_bindings: list[KbBinding] = Field(default_factory=list)   # đổi tên, số nhiều, CÓ THỂ rỗng
    # golden_set_ref: str  — XOÁ khỏi Recipe
```

**`kb_id` bị bỏ, không giữ lại rename.** Từ Q4=(a), danh tính một KB chính là tên `section_role`
của nó — giữ cả `kb_id` lẫn `section_role` trên cùng một binding là 2 field cho 1 sự thật, đúng
loại trùng lặp `/simplify` review vẫn bắt. Nếu Q4 sau này lật sang (b) (`kb.knowledge_bases` có
danh tính riêng), đó là lúc `kb_id` quay lại — cùng RFC riêng, không phải bây giờ.

**`golden_set_ref` bị xoá khỏi `Recipe`, không đổi thành `list[str]`.** Lý do: `golden_autogen.py:93`
đã có quy ước đặt tên xác định — `f"kb-{section_role}-auto-v1"`. Với N binding, N bộ golden **suy ra
được thẳng từ danh sách `kb_bindings`**, không cần lưu song song một field dễ lệch pha với binding
(gõ tay 2 field cho cùng 1 sự thật là đúng loại lỗi cả `Q2` lẫn Q4 đang tránh). Agent zero-KB
(`kb_bindings=[]`, Q3 — AIE-2) tự nhiên có 0 bộ golden, không cần giá trị rỗng đặc biệt kiểu
`golden_set_ref=""`.

Đây là điểm khác với 2 lựa chọn issue #239 tự đặt ra ban đầu ("`golden_set_ref` chuyển vào trong
từng binding" hay "giữ ở cấp recipe, đổi `list[str]`") — đề xuất một hướng thứ 3: **không lưu field
này nữa, suy ra tại chỗ dùng**. Cần AIE-2 xác nhận quy ước đặt tên đủ ổn định để suy ra được (không
có KB nào cần override tên bộ golden khác quy ước) trước khi chốt hướng này.

## Việc kéo theo theo package

| Package | File | Việc |
|---|---|---|
| `contracts` | `recipe.py:86-90,114-129` | Đổi `KbBinding`/`Recipe` như trên. Bump `SCHEMA_VERSION` (rename + required→optional-list là breaking, docstring dòng 8-10 tự ghi rõ). |
| `workbench` | `recipe.py:62-109` (`create_recipe`) | Mở tham số `kb_bindings: list[KbBinding] \| None` thật (đóng lại đúng thứ workbench#41 đã đóng, nhưng số nhiều thay vì số ít như `create_recipe_d4` cũ). |
| `workbench` | `validator.py:139-160` (`agent_shape_lint`) | `kb_binding.kb_id_non_blank`/`kb_binding.scope_non_blank`/`golden_set_ref.non_blank` (3 luật) → thay bằng luật trên `kb_bindings` (mỗi phần tử `section_role` không rỗng, không trùng `section_role` giữa các binding). |
| `engine` | `fence.py::fenced_kb_params` | **1 chỗ duy nhất** cần vá cho cả `interpreter.run()` lẫn `agent_loop.run_agent_loop()` (đã factor chung từ engine#33 phase 2-3): đổi override-toàn-bộ thành giao — `section_roles = [r for r in session_context.system_roles if r in {b.section_role for b in recipe.kb_bindings}]`. Cần thêm tham số `recipe`/binding scopes vào chữ ký hàm (hiện chỉ nhận `params`+`session_context`). |
| `engine` | `interpreter.py:183-184` (docstring) | Câu trích `_parse_kb_scope` đã trỏ tới hàm bị xoá 2026-08-24 (workbench#41/kit#218) — doc-drift có sẵn từ trước RFC này, dọn cùng lúc cho khỏi trỏ chết lần 2. |
| `evalhub` | `harness.py:752,819` + `core_set.py` | Theo đúng Q5/Q3 AIE-2 đã chốt trên #239 (AND từng bộ, ngân sách Core theo tổng, đường publish riêng cho `kb_bindings=[]`) — nằm ngoài phạm vi RFC này, AIE-2 tự làm song song. |
| `apps/studio` | `eval_adapter.py:153-208` (comment) | Cập nhật comment — hiện đang mô tả đúng hành vi CŨ (`kb_binding.scope` không phản ánh session), sẽ sai sau khi Q1=(b) implement (binding giờ ẢNH HƯỞNG thật, qua giao). |

## Rủi ro / điều chưa biết

- **Dữ liệu đã publish**: `wb.recipes` đã lưu recipe thật (IP tenant, theo comment `schema.py:39`).
  Rename `scope`→`section_role`, `kb_binding`→`kb_bindings` là breaking cho bất kỳ recipe cũ nào
  đọc lại. Chưa kiểm số lượng row bị ảnh hưởng — **cần AIE-2/SWE xác nhận** có cần path đọc-cũ-ghi-mới
  hay dữ liệu hiện tại toàn là seed/demo, xoá được.
- **`recipe_hash`**: đổi shape `Recipe` sẽ đổi hash mọi recipe hash lại từ payload mới — cùng loại
  rủi ro `AgentConfig.system_prompt` rename đã gặp (`recipe.py:67-75`, DEC-2), `publish.py::rollback()`
  cần giữ `history_recipe_hash` cũ nguyên vẹn, không recompute.
- **Đề xuất "suy ra `golden_set_ref` thay vì lưu"** là phần rủi ro nhất trong RFC này — nếu sai (có
  ca cần override tên bộ khác quy ước `kb-{role}-auto-v1`), phải quay lại phương án lưu field tường
  minh. Xin ý kiến AIE-2 trước khi implement, đừng chỉ ký cho qua.

## Cần ký

4/4 (DE · SWE · AIE-1 · AIE-2) theo GITFLOWS.md §2, vì đây là required-shape-change trên
`packages/contracts`. Mentor duyệt merge (CODEOWNERS `contracts` = mentor) sau khi đủ 4/4.

| Thành viên | Trạng thái |
|---|---|
| AIE-1 — Trần Bá Đạt | ✅ tác giả — đề xuất |
| DE — Nguyễn Đông Anh | ⬜ chưa ký |
| SWE — Thiệu Quang Minh | ⬜ chưa ký |
| AIE-2 — Lưu Tiến Duy | ⬜ chưa ký — đặc biệt xin ý kiến mục "suy ra `golden_set_ref`" ở trên |
