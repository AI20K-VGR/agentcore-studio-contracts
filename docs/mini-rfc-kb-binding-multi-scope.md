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

**Đã vá 2026-08-26** — `agentcore-studio-workbench` PR #50 (CI xanh), độc lập RFC này: `create_recipe()`
nhận thêm `kb_binding: KbBinding | None = None`, additive-only, không đụng `packages/contracts`, shape
vẫn số ít như hôm nay. Giữ nguyên đoạn dưới làm hồ sơ — gap này **không còn chặn** phần shape N-KB của
RFC, nhưng RFC vẫn phải đổi chữ ký `create_recipe`/`agent_shape_lint` sang số nhiều khi Q2 merge (bảng
"Việc kéo theo" bên dưới).

`packages/workbench/src/studio_workbench/recipe.py:62-96` (trước PR #50):

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
nới kiểu `str` → `list[str]`, mà còn phải **mở lại đường tham số hoá** đã đóng ở workbench#41 (PR #50
mở lại cho shape số ít; số nhiều vẫn chờ Q2).

### 3. Default production KHÔNG theo quy ước tự sinh — xung đột thật với "suy ra `golden_set_ref`" (scan 2026-08-26, chưa nêu trong kit#239)

`golden_autogen.py:93` sinh `f"kb-{section_role}-auto-v1"`, nhưng **default đang chạy production
không theo quy ước đó**:

```
packages/workbench/src/studio_workbench/recipe.py:77   golden_set_ref: str = "callisto-golden-30-v1"
apps/studio/src/studio_app/routes/publish.py:82        golden_set_ref: str = "callisto-2.0-golden-30-v1"
```

`callisto-golden-30-v1`/`callisto-2.0-golden-30-v1` là bộ **viết tay**, có trước `app#61` (golden
tự sinh theo `section_role`), và đang sống thật trong `test_recipe.py:121`, `test_golden_seed.py:68,80`,
`test_gate2_*` — không phải mã chết xoá được tuỳ tiện. Nếu `golden_set_ref` bị xoá khỏi `Recipe` và suy
ra thuần từ `section_role` như đề xuất gốc bên dưới, **mọi recipe dùng default hiện tại mất bộ chấm**
ngay khi Q2 merge — đây là hệ quả thật, không còn là rủi ro giả định (mục "Rủi ro" cũ đã tự gắn cờ
đúng chỗ này, giờ có bằng chứng).

## Đề xuất shape

```python
class KbBinding(BaseModel):
    model_config = ConfigDict(frozen=True)

    section_role: str                    # đổi tên từ `scope` — khớp thẳng Q4=(a), bỏ `kb_id`
                                           # (dư thừa: "1 KB" = section_role, không còn danh tính riêng)
    golden_set_ref: str | None = None     # None => suy ra "kb-{section_role}-auto-v1"
                                           # str  => override tường minh (bộ viết tay/pre-app#61)

class Recipe(BaseModel):
    ...
    kb_bindings: list[KbBinding] = Field(default_factory=list)   # đổi tên, số nhiều, CÓ THỂ rỗng
    # golden_set_ref: str  — XOÁ khỏi Recipe (chuyển vào từng KbBinding, xem trên)
```

**`kb_id` bị bỏ, không giữ lại rename.** Từ Q4=(a), danh tính một KB chính là tên `section_role`
của nó — giữ cả `kb_id` lẫn `section_role` trên cùng một binding là 2 field cho 1 sự thật, đúng
loại trùng lặp `/simplify` review vẫn bắt. Nếu Q4 sau này lật sang (b) (`kb.knowledge_bases` có
danh tính riêng), đó là lúc `kb_id` quay lại — cùng RFC riêng, không phải bây giờ.

**`golden_set_ref` chuyển vào TỪNG `KbBinding`, optional, mặc định suy ra — sửa 2026-08-26 sau khi
scan tìm ra mục "Vấn đề #3" ở trên.** Bản gốc RFC định xoá hẳn field này khỏi mọi nơi ("suy ra tại
chỗ dùng"), nhưng `callisto-golden-30-v1`/`callisto-2.0-golden-30-v1` là bằng chứng thật của một ca
"tên bộ khác quy ước" mà bản gốc coi là rủi ro giả định — nên field không biến mất, nó **chuyển cấp**
từ `Recipe` (1 field, bắt buộc) xuống từng `KbBinding` (1 field, optional):

- `golden_set_ref=None` (mặc định) → suy ra `f"kb-{section_role}-auto-v1"` — đường mặc định cho
  KB thật gắn qua canvas (mọi KB từ `app#61` upload đều có bộ tự sinh đúng quy ước, không cần khai
  tay). Đây vẫn là hướng chính RFC nhắm tới — override chỉ là lối thoát cho ca cũ, không phải quay
  lại lưu-mọi-thứ-tường-minh.
- `golden_set_ref="callisto-golden-30-v1"` (hoặc bất kỳ tên nào) → dùng đúng giá trị đó, không suy
  ra. Đây là đường tương thích ngược cho `create_recipe`'s default hiện tại và mọi test đang neo vào
  `callisto-golden-30-v1`/`callisto-2.0-golden-30-v1` (`test_recipe.py:121`, `test_golden_seed.py`,
  `test_gate2_*`) — chúng tiếp tục sống nguyên, chỉ đổi chỗ khai từ `Recipe.golden_set_ref` sang
  `KbBinding.golden_set_ref`.

Agent zero-KB (`kb_bindings=[]`, Q3 — AIE-2) vẫn tự nhiên có 0 bộ golden, không cần giá trị rỗng đặc
biệt kiểu `golden_set_ref=""` — không đổi so với bản gốc.

Đây vẫn là hướng thứ 3 so với 2 lựa chọn issue #239 tự đặt ra ("chuyển vào từng binding" hay "giữ ở
cấp recipe, đổi `list[str]`") — chỉ khác bản gốc RFC ở chỗ field **không biến mất hoàn toàn**, nó
optional với default suy-ra. AIE-2 vẫn cần xác nhận: có ca `golden_set_ref` nào KHÁC quy ước ngoài
2 cái `callisto-*` đã biết không (đặc biệt là dữ liệu tenant thật ngoài demo/seed)? Nếu có, override
field này đã đỡ được — chỉ cần điền đúng tên, không cần sửa RFC lần nữa.

## Việc kéo theo theo package

| Package | File | Việc |
|---|---|---|
| `contracts` | `recipe.py:86-90,114-129` | Đổi `KbBinding`/`Recipe` như trên. Bump `SCHEMA_VERSION` (rename + required→optional-list là breaking, docstring dòng 8-10 tự ghi rõ). |
| `workbench` | `recipe.py:62-109` (`create_recipe`) | **Đã mở tham số số ít** (`kb_binding: KbBinding \| None`, PR #50, 2026-08-26). Còn lại: đổi số ít → `kb_bindings: list[KbBinding] \| None` khi Q2 merge — chữ ký đã có tiền lệ optional-param nên đổi tiếp không phải mở đường lần đầu. |
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
- **Đề xuất "suy ra `golden_set_ref` thay vì lưu"** — **đã sửa 2026-08-26**: field không xoá hẳn nữa,
  chuyển thành `KbBinding.golden_set_ref: str | None = None` (suy ra khi `None`, override khi có giá
  trị). Lý do sửa: scan tìm ra `callisto-golden-30-v1`/`callisto-2.0-golden-30-v1` là default đang
  chạy production, không theo quy ước — bản gốc coi đây là rủi ro giả định, giờ là xung đột thật (mục
  "Vấn đề #3"). Còn lại cần AIE-2 xác nhận: có `golden_set_ref` nào khác quy ước NGOÀI 2 cái đã biết
  không (tenant thật, không phải demo/seed) — nếu có, override field đã đỡ được, không cần sửa RFC.

## Cần ký

4/4 (DE · SWE · AIE-1 · AIE-2) theo GITFLOWS.md §2, vì đây là required-shape-change trên
`packages/contracts`. Mentor duyệt merge (CODEOWNERS `contracts` = mentor) sau khi đủ 4/4.

| Thành viên | Trạng thái |
|---|---|
| AIE-1 — Trần Bá Đạt | ✅ tác giả — đề xuất |
| DE — Nguyễn Đông Anh | ⬜ chưa ký |
| SWE — Thiệu Quang Minh | ⬜ chưa ký |
| AIE-2 — Lưu Tiến Duy | ⬜ chưa ký — mục "suy ra `golden_set_ref`" đã có override field giải xung đột `callisto-*`; cần xác nhận không còn ca nào khác quy ước ngoài 2 cái đã biết |
