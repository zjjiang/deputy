# Design: filter-archived-by-time

## Context

- `projects` 表无任何时间列；`set_stage`（`app/store/projects.py:189`）按 `STAGE_TRANSITIONS` 状态机迁移，`archived` 是终态，但 `unarchive()`（`projects.py:311`）可以直接把归档项目迁回其他态——两处都要维护 `archived_at`。
- 时间戳写法沿用 `toggle_todo` 的既有约定：store 函数收 `now: str | None = None`，API 层传 `datetime.now().isoformat()`（`app/api.py:166`）。
- 已有幂等迁移先例：`todos.done_at`（`app/store/db.py:148-151`，`PRAGMA table_info` 检查后 `ALTER TABLE`）。
- 看板渲染层已有同型过滤：todo 完成项只显示 30 天内（`app/web/index.html` projectCard，`TODO_VISIBLE_MS`）。

## Goals / Non-Goals

- Goals：归档时间在真源可查；看板归档桶 30 天过滤；对 MCP/门禁零影响。
- Non-Goals：不给项目加 created_at/updated_at 等其余时间戳；不做"归档桶展开查看全部"入口；不清理真源数据。

## Decisions

1. **列名 `archived_at TEXT`，NULL 表示未归档/历史归档** —— 与 `todos.done_at` 对称（完成记、取消清），历史数据留 NULL 不回填猜测值；NULL 在看板语义上等同"超期隐藏"。
2. **时间戳在 `set_stage` 内部维护，而非调用方负责** —— `set_stage` 与 `archive()`（内部转调 `set_stage`）、以及未来经门禁 approve 派发的路径全部自动覆盖；`unarchive()` 自己直接 UPDATE，单独清空。备选"由 API 层写"被否：会漏掉门禁派发路径，且违反红线 3（规则在 store 层）。
3. **看板过滤放渲染层，不放 store 查询** —— 真源读接口保持全量（契约不变），"看板只显示最近"是展示策略，与 todo 过滤同层同模式；30 天常量 `ARCHIVED_VISIBLE_MS` 与 `TODO_VISIBLE_MS` 并列。
4. **`now` 参数默认 `datetime.now().isoformat()`（本地时间）** —— 与 `/api/state` 现有 `done_at` 取值口径一致（`api.py:166` 用本地时间），测试显式传 `now` 保证确定性。

## Risks / Trade-offs

- [本地时间无时区后缀，30 天窗口跨夏令时有 ±1h 误差] → 可接受：过滤粒度是天级展示，不用于审计。
- [历史归档项目被隐藏后，用户想找回只能查库] → 本期接受（proposal 已向用户确认）；后续如需要可在归档桶加"显示全部"开关，另立 change。
- [迁移对每个已存在的库生效（公司/Mac mini 两处部署）] → `ALTER TABLE ADD COLUMN` 幂等且向后兼容，部署即自动迁移，无需手工步骤。

## Migration Plan

`init_db()` 在 SCHEMA 中新增列定义（新库直建），并对旧库做 `PRAGMA table_info(projects)` 检查后 `ALTER TABLE projects ADD COLUMN archived_at TEXT`。回滚：列多余无害，代码回退即可，无需数据回滚。

## Open Questions

（无）
