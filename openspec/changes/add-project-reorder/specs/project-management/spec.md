## ADDED Requirements

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
