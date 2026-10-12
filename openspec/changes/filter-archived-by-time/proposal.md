# Proposal: filter-archived-by-time

## Why

作战室的归档桶会无限累积：项目归档后一直显示在页面上，几个月后翻找进行中的项目越来越费劲。用户要求与 todo 一致的显示规则——**未完成的全显，已完成的只留最近一个月**。项目（归档）目前没有任何时间戳，`projects` 表只有 `id/name/stage/drive/kind/trigger/ord`，无法按时间过滤，因此需要真源先记下"何时归档"。

## What Changes

- `projects` 表新增 `archived_at TEXT` 列（可 NULL）：
  - `set_stage` 迁入 `archived` 时写入时间戳；`unarchive` 迁出时清空。
  - 幂等迁移：已有库 `ALTER TABLE` 补列，历史归档项目 `archived_at` 为 NULL（视为"很久以前归档"，被看板隐藏，符合直觉）。
- `/api/state` 的项目序列化带上 `archived_at`。
- 看板归档桶只显示**最近 30 天内归档**的项目；其余桶（未完成）不受影响，全显。
- 纯 UI 端不新增数据；过滤在看板渲染层做（与 todo 30 天过滤同一模式），时间戳的产生与清空规则在 store 层强制（红线 3）。

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `project-management`：
  - 新增需求：项目迁入归档态时系统 SHALL 记录 `archived_at`，迁出归档态时 SHALL 清空它。
  - 新增需求：看板归档桶 SHALL 只显示最近 30 天内归档的项目（无时间戳的历史归档视为超期隐藏）；其他桶的显示不受影响。

## Impact

- `app/store/db.py`：SCHEMA 加列 + `init_db` 幂等迁移（沿用 `done_at` 先例）。
- `app/store/projects.py`：`set_stage` / `unarchive` 维护 `archived_at`；`_project_row_to_dict` 带出字段。
- `app/web/index.html`：作战室归档桶渲染时按 30 天过滤。
- 测试：`tests/test_projects_store.py`（时间戳写入/清空/迁移）与看板序列化；不改任何 MCP 工具与门禁逻辑，`tests/test_mcp_contract.py` 不受影响。
