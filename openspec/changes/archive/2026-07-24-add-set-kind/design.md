## Context

`kind`（biz/tool）在 `add_project` 时写入 `projects.kind` 列，之后没有任何修改路径。store 层已有同构的属性修改函数 `set_drive`、`set_stage`、`set_trigger`，本 change 照 `set_drive` 的模式补 `set_kind` 即可，不引入新范式。

## Goals / Non-Goals

**Goals:**
- 已有项目可修改 kind（biz ↔ tool）。
- 分身经门禁提议改 kind；用户在看板直接改。
- 与 set_drive 完全同构，最小改动。

**Non-Goals:**
- 不给 kind 加状态机/约束（biz↔tool 任意互转都合理，与 stage 不同）。
- 不改数据库 schema（kind 列已存在）。
- 不做批量改 kind。

## Decisions

- **store.set_kind(project_id, kind)**：校验 `kind in VALID_KINDS`，否则抛 `DomainError`；`_require_project` 确认存在；`transaction()` 内 `UPDATE projects SET kind=?`；返回 `get_project(...)`。逐行照抄 `set_drive`，只换字段名与校验集。
- **domain.PROPOSAL_ACTIONS** 加 `"set_kind": ("project_id", "kind")`。
- **store._DISPATCH** 加 `"set_kind": lambda a: set_kind(a["project_id"], a["kind"])`，使已批准的提议能派发执行。
- **mcp_server.propose** docstring 的 action 列表补一行 `set_kind {project_id, kind}`。
- **api**：新增 `ProjectKind(BaseModel){project_id, kind}` 与 `POST /api/project/kind`，走 `_guard`，与 `/api/project/stage` 一致（用户直接改，不入提议队列）。

## Risks / Trade-offs

- 风险极低：无 schema 变更、无破坏性、纯增量。
- 唯一注意点：门禁一致性——分身**只能**经 `propose(set_kind, ...)` 改，API 的 `/api/project/kind` 是给用户（看板）用的，与现有 set_stage/set_drive 的双路径设计一致，不破坏"分身不能直写真源"红线（MCP 侧不暴露直写工具，契约测试保证）。
