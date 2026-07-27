## ADDED Requirements

### Requirement: todo 完成时记录时间戳
系统 SHALL 在 todo 被标记为完成时记录完成时间（done_at），在取消完成时清空该时间。该时间戳 SHALL 在 API 返回的 todo 对象中可见。

#### Scenario: 标记完成记录时间
- **WHEN** todo 被标记为 done=true
- **THEN** 该 todo 的 done_at 被设为操作发生的时间（ISO 格式）

#### Scenario: 取消完成清空时间
- **WHEN** 已完成的 todo 被标记为 done=false
- **THEN** 该 todo 的 done_at 被清空为 null

#### Scenario: API 返回包含 done_at
- **WHEN** 通过 API 获取项目状态
- **THEN** 每个 todo 对象包含 done_at 字段（已完成的有 ISO 时间值，未完成的为 null）

#### Scenario: 门禁批准的 toggle 也记录时间
- **WHEN** 分身提议 toggle_todo 并被用户批准
- **THEN** done_at 记录的是批准（approve）时刻，而非提议时刻

#### Scenario: 已有数据兼容
- **WHEN** 系统启动且存在未迁移的旧 todo 数据（无 done_at 列）
- **THEN** 自动加列，已有记录 done_at 为 null，系统正常运行不报错
