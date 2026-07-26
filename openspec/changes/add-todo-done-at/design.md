## Context

deputy 的时间戳惯例：store 层不自己取时钟，时间由调用层传入（`now` 参数，ISO 字符串如 `2026-07-24T10:30:00`）。proposals 表的 created/decided 已遵循此模式。toggle_todo 目前无时间参数。

## Goals / Non-Goals

**Goals:**
- todo 完成时记 done_at（ISO 时间戳）；取消完成时清空。
- 遵循现有 now 参数惯例（可测试、可复现）。
- 已有数据无损兼容。

**Non-Goals:**
- 不做 created_at（创建时间）。
- 不做周报/digest 端点（那是消费者，等消费者出现再铺）。
- 不改 UI 展示 done_at（先做数据层，展示以后按需加）。

## Decisions

- **Schema 迁移**：`ALTER TABLE todos ADD COLUMN done_at TEXT`。放在 `app/db.py` 的初始化逻辑里（检测列不存在则加,幂等）。不新建迁移文件——项目还没到需要正式 migration 系统的阶段。
- **toggle_todo(project_id, todo_id, done, now)**：新增 `now: str` 参数。
  - `done=True` → `UPDATE todos SET done=1, done_at=? WHERE ...`
  - `done=False` → `UPDATE todos SET done=0, done_at=NULL WHERE ...`
- **API 层**：`/api/todo/toggle` 在调用 store 前取 `datetime.now().isoformat()` 作为 now 传入。
- **proposals dispatch**：`_DISPATCH["toggle_todo"]` 在 approve 时由 `proposals.approve` 传入 approve 的 now（提议批准的那一刻=生效时间）。
- **返回格式**：`get_project` 已有序列化 todo 的逻辑，在那里加 `"done_at": row["done_at"]`（可能为 None）。

## Risks / Trade-offs

- 唯一风险：`ALTER TABLE ADD COLUMN` 在 SQLite 是安全操作(不锁表、不丢数据)，但要确保 `get_project` 读取新列时旧行(done_at=NULL)不炸 —— 靠允许 None 保证。
- 用户侧分身 propose toggle_todo 后 approve，done_at 记的是 approve 时间而非 propose 时间。这语义正确：提议入队不代表完成，批准才代表完成。
