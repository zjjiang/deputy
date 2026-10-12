# Tasks: filter-archived-by-time

## 1. 真源：archived_at 记录与清空（TDD）

- [x] 1.1 Red：新建 `tests/test_projects_store.py`——迁入归档态写入 `archived_at`（经 `set_stage` 与 `archive` 两路）、`unarchive` 清空、非归档态为 None、`now` 参数显式注入。跑 `uv run pytest -q` 确认新测试失败。
- [x] 1.2 Green：`app/store/db.py` SCHEMA 给 `projects` 加 `archived_at TEXT` + `init_db()` 幂等迁移（沿用 `done_at` 先例）；`app/store/projects.py` 的 `set_stage`（迁入 archived 写入）与 `unarchive`（迁出清空）维护时间戳，`_project_row_to_dict` 带出字段。跑 `uv run pytest -q` 确认通过。
- [x] 1.3 Red→Green：补迁移测试——旧库（无 `archived_at` 列、含归档项目）经 `init_db()` 补列且历史归档项目 `archived_at` 为 NULL。合入 1.2 一起验证。

## 2. 看板：归档桶 30 天过滤

- [x] 2.1 `app/web/index.html` renderBoard：归档桶项目按 `archived_at` 过滤（30 天内才显示，`ARCHIVED_VISIBLE_MS` 与 `TODO_VISIBLE_MS` 并列；NULL 隐藏），概览条计数与分区标题跟随过滤后的数量。浏览器刷新确认：归档超 30 天/无时间戳的项目不再出现，其余桶不变。

## 3. 回归与收尾

- [x] 3.1 `uv run pytest -q` 全绿（含 `tests/test_mcp_contract.py`——本次不碰 MCP 工具面，守门测试必须原样通过）。
