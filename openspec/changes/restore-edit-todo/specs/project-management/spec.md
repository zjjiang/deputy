## ADDED Requirements

### Requirement: 看板提供修改 todo 文字的入口
看板的每条 todo SHALL 提供一个修改文字的入口，修改后保留该 todo 的完成状态与 done_at（不重建）。

#### Scenario: 修改 todo 文字
- **WHEN** 用户在看板点击某 todo 的"改"入口并输入新文字
- **THEN** 该 todo 文字更新，done/done_at 状态不变

#### Scenario: 每条 todo 都有改入口
- **WHEN** 渲染项目卡片的 todo 列表
- **THEN** 每条 todo 行都含"改"与"删除"两个入口
