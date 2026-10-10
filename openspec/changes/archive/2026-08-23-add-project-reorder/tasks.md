## 1. Store 层：`reorder_project` + `add_project` 撞号修正（TDD）

- [x] 1.1 写测试：`reorder_project` 把项目插到 target 前/后，验证 `ord` 重新编号为连续整数（`tests/test_gate.py` 或新建 `tests/test_reorder.py`），先跑确认失败
- [x] 1.2 写测试：`target_id == project_id` 视为无操作，返回当前项目、`ord` 不变
- [x] 1.3 写测试：`project_id` 或 `target_id` 不存在时抛 `KeyError`
- [x] 1.4 写测试：非法 `position`（不属于 before/after）抛 `domain.DomainError`
- [x] 1.5 写测试：删除项目后新建项目，新 `ord` 不与现有项目撞号
- [x] 1.6 在 `app/store/projects.py` 实现 `reorder_project(project_id, target_id, position)`：整表按当前 `ord,id` 读出、在内存列表中重新排列、整表重写连续 `ord`，包在 `transaction()` 内
- [x] 1.7 修正 `add_project` 的 `ord` 赋值：从 `COUNT(*)` 改为取当前最大 `ord`+1（无项目时为 0）
- [x] 1.8 运行测试确认全部通过（Green）

## 2. 门禁：`reorder_project` 纳入提议白名单（TDD）

- [x] 2.1 写测试：`propose("reorder_project", {...})` 生成 pending 提议，真源 `ord` 不变
- [x] 2.2 写测试：approve 后 `ord` 才按新顺序更新
- [x] 2.3 写测试：`tests/test_mcp_contract.py` 的 `forbidden` 集合自动覆盖新 action（确认现有测试逻辑无需改动，`domain.PROPOSAL_ACTIONS` 变化后自动生效）
- [x] 2.4 在 `app/domain.py` 的 `PROPOSAL_ACTIONS` 新增 `"reorder_project": ("project_id", "target_id", "position")`
- [x] 2.5 在 `app/store/projects.py` 的 `_DISPATCH` 新增 `reorder_project` 派发
- [x] 2.6 运行测试确认全部通过（Green）

## 3. API：用户直接操作端点

- [x] 3.1 写测试（`tests/test_api.py`）：`POST /api/project/reorder` 成功场景、404（不存在）、400（非法 position）
- [x] 3.2 在 `app/api.py` 新增 `ProjectReorder` 请求体（`project_id`, `target_id`, `position`）与 `/api/project/reorder` 端点，走 `_guard`
- [x] 3.3 运行测试确认全部通过（Green）

## 4. MCP：更新 propose 工具文档

- [x] 4.1 在 `app/mcp_server.py` 的 `propose` 工具 docstring 补充 `reorder_project {project_id, target_id, position}` 说明
- [x] 4.2 运行 `tests/test_mcp_contract.py` 确认工具集不变（`reorder_project` 未作为直写工具泄漏）

## 5. 前端：卡片排序入口

- [x] 5.1 在 `app/web/index.html` 的 `projectCard` 渲染逻辑中，基于 `byBucket` 过滤后的数组计算每个项目在所属桶内的上一个/下一个邻居 id
- [x] 5.2 卡片增加上移/下移按钮，点击时调用 `POST /api/project/reorder`（携带邻居 id 作为 target_id、对应 position）并刷新看板
- [x] 5.3 桶内首位隐藏上移按钮、末位隐藏下移按钮
- [x] 5.4 手动验证：启动 `uv run uvicorn app.api:app --port 8899`，在浏览器里对同一桶内多个项目点击上移/下移，确认顺序变化且刷新后保持

## 6. 收尾

- [x] 6.1 `uv run pytest -q` 全绿
- [x] 6.2 确认 `tests/test_mcp_contract.py` 仍通过（门禁红线未破）
