## Why

todo 打勾后没有记录完成时间。将来做周报/复盘时需要查"本周完成了哪些 todo"，而当前只有 done 布尔，无法按时间筛选。done_at 是"todo 时间维度"的第一块砖——无论未来周报怎么做(自动/手动/周记)，这个字段都用得上、不会白做。

## What Changes

- todos 表新增 `done_at` 列（TEXT，ISO 时间字符串，可空）。
- `toggle_todo` 新增 `now` 参数（遵循现有 proposals 的惯例：时间由调用层传入，store 不碰时钟）：
  - done=true → 写入 `done_at = now`
  - done=false → 清空 `done_at = NULL`
- API 层 `/api/todo/toggle` 负责取当前时间传给 store。
- MCP 层 `propose(toggle_todo)` 通过 dispatch 调用时同样传时间（approve 时刻的时间）。
- API 返回的 todo 对象带上 `done_at` 字段（已完成的有值，未完成的为 null）。
- 已有数据：现有已完成的 todo，`done_at` 留空（历史无法追溯，诚实留空，不伪造）。

## Capabilities

### Modified Capabilities
- `project-management`: 已有 spec 约束了 kind 展示和界面规范；本 change 增加"todo 完成时记录时间戳"这条数据要求。

## Impact

- Schema：todos 表 `ALTER TABLE ADD COLUMN done_at TEXT`（SQLite 原生支持 ADD COLUMN，无需重建表）。
- 代码：`app/store/projects.py`（toggle_todo）、`app/api.py`（传 now）、`app/store/proposals.py`（dispatch 时传 now）。
- 测试：TDD——done→有时间戳、undone→清空、旧数据(done_at=NULL)不炸、门禁批准 toggle 也记时间。
- 无破坏性变更（done_at 可空，旧数据自然兼容）。
- 无新依赖。

## 未来扩展（本次不做，留痕）

- journal 表（随手丢进展）+ /api/weekly-digest（周报素材端点）—— 等周报 workflow 真正开始搞时再铺。
- todo 的 created_at —— 可看"挂了多久才做"，但非当前必需。
- 项目 stage 变更历史 —— 复盘要"这个月状态变了几次"时再加。
