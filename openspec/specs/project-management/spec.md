# project-management Specification

## Purpose
TBD - created by archiving change add-set-kind. Update Purpose after archive.
## Requirements
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

### Requirement: 看板展示项目 kind
看板的项目卡片 SHALL 展示该项目的 kind，让用户一眼区分商业项目（biz）与自用工具（tool）。该展示为只读且 SHALL 使用纯文字标签（"商业" / "工具"），不使用 emoji 图标，不提供在卡片上直接编辑 kind 的控件。

#### Scenario: 商业项目显示商业角标
- **WHEN** 渲染一个 kind 为 biz 的项目卡片
- **THEN** 卡片上出现纯文字"商业"角标（无 emoji 标识）

#### Scenario: 自用工具显示工具角标
- **WHEN** 渲染一个 kind 为 tool 的项目卡片
- **THEN** 卡片上出现纯文字"工具"角标（无 emoji 标识）

#### Scenario: 卡片不提供 kind 编辑控件
- **WHEN** 查看项目卡片
- **THEN** 卡片上没有修改 kind 的下拉框或按钮（改 kind 走分身提议或其他入口）

### Requirement: 界面不使用装饰性 emoji
看板界面 SHALL 不使用装饰性 emoji 表达状态、分区或操作，改用文字标签、语义色与排版层级。通用无歧义符号（如勾选 ✓、删除 ×）不受此限。

#### Scenario: 项目状态以文字呈现
- **WHEN** 渲染项目卡片的状态选择器
- **THEN** 各状态选项为纯文字（火花/验证/主攻/运营/维护/雪藏/归档），不含 emoji

#### Scenario: 分区标题以文字呈现
- **WHEN** 渲染 tab 栏与各分区（全盘/门禁/需求池、此刻聚焦）
- **THEN** 标题为纯文字，不含 emoji 图标

### Requirement: 看板按桶分组呈现
全盘视图 SHALL 将项目按生命周期桶（主攻/运营/维护/探索/雪藏/归档）分组呈现，而非单一平铺列表；主攻项目 SHALL 获得最强视觉权重，雪藏/归档 SHALL 视觉弱化。空桶不呈现分区标题。

#### Scenario: 项目按桶分组
- **WHEN** 渲染全盘视图且存在多个不同 stage 的项目
- **THEN** 项目按其所属桶分组显示，每个非空桶有一个文字分区标题（含该桶项目计数）

#### Scenario: 主攻最重、雪藏最弱
- **WHEN** 同时存在 attack 与 frozen 项目
- **THEN** attack 项目视觉权重最高（整行/大字/强调左边），frozen 项目视觉弱化（降饱和）

### Requirement: 桶位概览
全盘视图 SHALL 在顶部提供一个桶位概览，展示各桶的项目计数，让用户一眼看到全盘分布。

#### Scenario: 概览显示各桶计数
- **WHEN** 渲染全盘视图
- **THEN** 顶部出现概览条，列出各非空桶的名称与项目数量

### Requirement: 此刻聚焦作为报头
全盘视图 SHALL 将"此刻聚焦"作为页面最醒目的报头区块呈现，视觉权重高于普通项目卡片。

#### Scenario: 焦点报头醒目
- **WHEN** 渲染全盘视图
- **THEN** 此刻聚焦区块在视觉上明显区别于并重于下方项目卡片

