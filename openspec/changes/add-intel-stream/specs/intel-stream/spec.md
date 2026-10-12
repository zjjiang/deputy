## Purpose

军情处的「翻阅」面：在 deputy 军情 tab 内主动浏览 feed-curator 语料流（四星文章、各领域论文/仓库/文章），奏折与情报流同区呈现。deputy 只做渲染与代理——文档实体、阅读状态的存储全部留在 feed-curator（状态跟着实体走）。

## ADDED Requirements

### Requirement: 情报流浏览
军情 tab SHALL 提供「情报流」分区：以卡片流呈现 feed-curator 语料（标题/类型/领域/星级/摘要/已读收藏标识），支持按领域、类型（article/paper/repo）、仅四星（stars≥4）筛选，按时间或星级排序，分页浏览（每页默认 30，以 feed-curator 返回的 total 驱动翻页）。数据 SHALL 经 deputy 后端代理端点转发自 feed-curator `GET /api/docs`，deputy 不落库。

#### Scenario: 按领域与四星筛选
- **WHEN** 用户选择领域「具身智能」并勾选「仅四星」
- **THEN** deputy 代理转发筛选参数至 feed-curator（含 sort=stars 与 min_stars=4），情报流仅呈现该领域四星及以上条目

#### Scenario: 分页
- **WHEN** 用户翻到下一页
- **THEN** 代理按 offset 转发，翻页控件以 feed-curator 返回的 total 为准

### Requirement: 阅读状态代理写回
情报流条目的「已读」「收藏」操作 SHALL 由 deputy 代理转发至 feed-curator `POST /api/docs/{doc_id}/reading`；阅读状态的存储 SHALL 全部留在 feed-curator `reading` 表，deputy SHALL NOT 存储任何文档阅读状态。代理成功后 SHALL 以 feed-curator 返回的最新状态刷新展示。

#### Scenario: 标记已读
- **WHEN** 用户在情报流对某条目点「已读」
- **THEN** deputy 转发写回 feed-curator 并按返回状态刷新该条目标识；deputy 自身库无任何变化

#### Scenario: 写回失败提示
- **WHEN** feed-curator 不可用导致代理写回失败
- **THEN** 用户收到失败提示，条目状态不变

### Requirement: curator 客户端与降级
deputy SHALL 以唯一集成出口（curator 客户端模块）访问 feed-curator：目标限本机 localhost（默认 `127.0.0.1:9003`，可配置）、请求设超时、失败返回结构化错误。feed-curator 不可用时 SHALL：情报流分区显示「图书馆闭馆」降级提示，**奏折分区不受影响**；写回操作返回失败。客户端 SHALL NOT 持有任何 feed-curator 数据副本。

#### Scenario: 图书馆闭馆降级
- **WHEN** feed-curator 服务不可用，用户打开军情 tab
- **THEN** 奏折分区正常呈现，情报流分区显示降级提示与重试入口

#### Scenario: 仅限本机
- **WHEN** 检查 curator 客户端配置
- **THEN** 默认目标为 127.0.0.1:9003，无对公网地址的调用（红线④不触碰）

### Requirement: 军情 tab 双区布局
军情 tab SHALL 呈现两个分区：奏折区（现有预设问题与版本化回答，行为不变）与情报流区（本能力）。分区 SHALL 有明确标识；情报流的筛选与分页状态 SHALL 在分区内自持，不干扰奏折区。界面 SHALL NOT 使用装饰性 emoji（沿用既有要求）。

#### Scenario: 双区同屏
- **WHEN** 用户打开军情 tab
- **THEN** 奏折区与情报流区以分区标识区分，各自独立滚动/交互

#### Scenario: 情报流筛选不影响奏折
- **WHEN** 用户在情报流切换筛选
- **THEN** 奏折区的列表与状态无任何变化

### Requirement: 章程更新——军情处三模式
CLAUDE.md 章程 SHALL将军情处模式修订为三种：奏折（定时/手动简报，进 deputy 存档）、面圣（微信即答，不落档）、**翻阅**（军情 tab 内浏览语料流，阅读状态存 feed-curator）。并 SHALL 写明集成出口约定：deputy 对 feed-curator 的全部 HTTP 访问只经 curator 客户端模块，代理不存储。

#### Scenario: 章程与实现一致
- **WHEN** 通读 CLAUDE.md 军情处条目
- **THEN** 三模式与状态归属表述与本能力的实际行为一致

### Requirement: 部署前提
本能力的运行前提 SHALL 是：feed-curator 与 deputy 同机，curator 客户端仅访问 localhost；无鉴权面扩大（红线④）。星级/摘要的**数据**可用性依赖 feed-curator 判定循环运行（fix-analysis-cycle）；未运行时情报流 SHALL 正常呈现（星级显示为空/「未判定」），不阻塞浏览。

#### Scenario: 未判定条目
- **WHEN** 语料中某文档从未被 AI 判定（stars 为空）
- **THEN** 情报流正常呈现该条目（星级显示「未判定」），不因缺失数据而隐藏或报错
