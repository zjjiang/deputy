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

#### Scenario: 商业项目显示商业标签
- **WHEN** 渲染一个 kind 为 biz 的项目卡片
- **THEN** 卡片上出现纯文字"商业"标签（无 emoji）

#### Scenario: 自用工具显示工具标签
- **WHEN** 渲染一个 kind 为 tool 的项目卡片
- **THEN** 卡片上出现纯文字"工具"标签（无 emoji）

#### Scenario: 卡片不提供 kind 编辑控件
- **WHEN** 查看项目卡片
- **THEN** 卡片上没有修改 kind 的下拉框或按钮

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

### Requirement: 看板提供修改 todo 文字的入口
看板的每条 todo SHALL 提供一个修改文字的入口，修改后保留该 todo 的完成状态与 done_at（不重建）。

#### Scenario: 修改 todo 文字
- **WHEN** 用户在看板点击某 todo 的"改"入口并输入新文字
- **THEN** 该 todo 文字更新，done/done_at 状态不变

#### Scenario: 每条 todo 都有改入口
- **WHEN** 渲染项目卡片的 todo 列表
- **THEN** 每条 todo 行都含"改"与"删除"两个入口

### Requirement: 项目在桶内排序
系统 SHALL 支持调整项目的展示顺序（`ord`），让用户能把重要的项目排到所属桶（主攻/运营/维护/探索/雪藏/归档）的前面。排序通过 `reorder_project(project_id, target_id, position)` 实现：把 `project_id` 插到 `target_id` 的前面（`position="before"`）或后面（`position="after"`），随后系统 SHALL 按新顺序重新编号全部项目的 `ord` 为连续整数（0,1,2,...）。该操作 SHALL 只感知全局 `ord` 序列，不感知"桶"的分组概念——桶是前端按 stage 过滤后的展示视图，同桶内挪动因过滤后仍保序而天然生效，不影响其他桶内项目的相对顺序。

用户 SHALL 能在看板直接调用此操作（不经门禁）；分身 SHALL 只能经门禁提议（`propose(reorder_project, ...)`）调用，不得直接写真源。

#### Scenario: 用户在看板挪动项目顺序
- **WHEN** 用户对某已存在项目提交 `POST /api/project/reorder` 且 `target_id` 指向另一个已存在项目、`position` ∈ {before, after}
- **THEN** `project_id` 被插到 `target_id` 指定的位置，全部项目的 `ord` 被重新编号为连续整数，返回更新后的项目

#### Scenario: 同桶内挪动不影响其他桶顺序
- **WHEN** 系统中存在跨多个 stage 的项目，用户挪动某个 attack 桶内项目的顺序
- **THEN** 其他桶（如 probe/frozen）内项目彼此的相对顺序不变

#### Scenario: target_id 与 project_id 相同视为无操作
- **WHEN** `reorder_project` 的 `target_id` 等于 `project_id`
- **THEN** 系统不改变任何项目的 `ord`，直接返回该项目当前状态

#### Scenario: project_id 或 target_id 不存在
- **WHEN** `reorder_project` 的 `project_id` 或 `target_id` 指向不存在的项目
- **THEN** 系统返回未找到错误（KeyError → HTTP 404），任何项目的 `ord` 不变

#### Scenario: 非法 position 被拒
- **WHEN** `position` 不属于 {before, after}
- **THEN** 系统拒绝并返回错误（DomainError → HTTP 400），任何项目的 `ord` 不变

#### Scenario: 分身经门禁提议排序
- **WHEN** 分身调用 `propose(reorder_project, {project_id, target_id, position}, reason)`
- **THEN** 生成一条 pending 提议且真源不变；仅当用户 approve 后，项目顺序才被重新编号

#### Scenario: 分身不能直接改排序
- **WHEN** 检查 MCP server 暴露的工具集
- **THEN** 不存在任何直接写排序的工具，`reorder_project` 只作为 `propose` 的 action 存在

#### Scenario: 新建项目不再因删除操作撞号
- **WHEN** 已有项目被删除后再新建一个项目
- **THEN** 新项目的 `ord` 大于当前所有项目的最大 `ord`，不与已有项目的 `ord` 冲突

### Requirement: 看板项目卡片提供排序入口
每张项目卡片 SHALL 提供上移/下移入口，在该项目当前所属桶（经 stage 过滤后的展示列表）内与相邻项目交换顺序。桶内首位的项目 SHALL 不显示上移入口，末位的项目 SHALL 不显示下移入口。

#### Scenario: 点击上移与所属桶内上一个邻居互换
- **WHEN** 用户点击某项目卡片的上移入口，且该项目在所属桶内不是首位
- **THEN** 该项目与所属桶过滤后列表中的上一个项目交换相对顺序

#### Scenario: 点击下移与所属桶内下一个邻居互换
- **WHEN** 用户点击某项目卡片的下移入口，且该项目在所属桶内不是末位
- **THEN** 该项目与所属桶过滤后列表中的下一个项目交换相对顺序

#### Scenario: 桶内首末位隐藏对应方向入口
- **WHEN** 渲染某桶内排在首位或末位的项目卡片
- **THEN** 首位项目不显示上移入口，末位项目不显示下移入口

