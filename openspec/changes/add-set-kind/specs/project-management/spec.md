## ADDED Requirements

### Requirement: 修改项目类型 kind
系统 SHALL 支持修改已有项目的 `kind`（`biz` 商业 / `tool` 自用工具），且仅接受这两个合法值。用户 SHALL 能在看板经 API 直接修改；分身 SHALL 只能经门禁提议（`propose(set_kind, ...)`）修改，不得直接写真源。

#### Scenario: 用户在看板修改 kind
- **WHEN** 用户对某已存在项目提交 `POST /api/project/kind` 且 kind ∈ {biz, tool}
- **THEN** 该项目的 kind 被更新，返回更新后的项目

#### Scenario: 非法 kind 被拒
- **WHEN** 提交的 kind 不属于 {biz, tool}
- **THEN** 系统拒绝并返回错误（DomainError → HTTP 400），项目 kind 不变

#### Scenario: 项目不存在
- **WHEN** 对不存在的 project_id 修改 kind
- **THEN** 系统返回未找到错误（KeyError → HTTP 404）

#### Scenario: 分身经门禁提议改 kind
- **WHEN** 分身调用 `propose(set_kind, {project_id, kind}, reason)`
- **THEN** 生成一条 pending 提议且真源不变；仅当用户 approve 后，项目 kind 才被更新

#### Scenario: 分身不能直接改 kind
- **WHEN** 检查 MCP server 暴露的工具集
- **THEN** 不存在任何直接写 kind 的工具，`set_kind` 只作为 `propose` 的 action 存在
