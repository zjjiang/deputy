# project-management 变更（delta）

## ADDED Requirements

### Requirement: 项目归档记录时间戳

系统 SHALL 在项目迁移到归档态（`archived`）时记录归档时间 `archived_at`；项目迁出归档态（`unarchive`）时系统 SHALL 清空 `archived_at`。非归档态的项目 `archived_at` SHALL 为空。`/api/state` 返回的项目数据 SHALL 包含 `archived_at` 字段。

#### Scenario: 迁入归档态写入时间戳

- **WHEN** 项目经 `set_stage` 或 `archive` 迁入 `archived` 态
- **THEN** 该项目的 `archived_at` 被写为当前时间（ISO 格式）
- **THEN** `/api/state` 中该项目带非空 `archived_at`

#### Scenario: 迁出归档态清空时间戳

- **WHEN** 归档项目经 `unarchive` 恢复到其他状态
- **THEN** 该项目的 `archived_at` 被清空

#### Scenario: 历史归档数据补列后时间戳为空

- **WHEN** 在已有数据库上做幂等迁移补出 `archived_at` 列
- **THEN** 已处于归档态的历史项目 `archived_at` 为 NULL（不回填猜测值）

### Requirement: 看板归档桶只显示最近归档

作战室看板 SHALL 在归档桶中只显示最近 30 天内归档的项目；归档超过 30 天或无归档时间（历史数据）的项目 SHALL 不在看板呈现。此过滤仅影响看板展示，SHALL 不删除或修改任何真源数据；其余桶（未归档项目）SHALL 不受影响。

#### Scenario: 最近归档的项目显示

- **WHEN** 项目在 30 天内归档
- **THEN** 它出现在作战室归档桶中

#### Scenario: 超期归档的项目隐藏

- **WHEN** 项目归档已超过 30 天，或 `archived_at` 为空（历史归档）
- **THEN** 它不出现在作战室归档桶中，真源数据保持不变
