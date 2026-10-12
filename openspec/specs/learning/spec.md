# learning Specification

## Purpose

讲武堂：系统学习模块。用户立学习主题，分身（龙虾）生成知识点大纲、在微信对话里按序授课，用户自评掌握进度，课程小结落回看板存档。进度驱动（用户发起），与军情处（定期动态简报）互不重叠。deputy 是账本与成绩单，龙虾是嘴，feed-curator 是图书馆。


## Requirements
### Requirement: 学习主题管理
用户 SHALL 能经看板/HTTP API 创建学习主题（track：标题 + 一句话学习目标），并可编辑、删除、调整其生命周期状态（active/paused/done）。分身 SHALL 只能经门禁提议创建（`add_track`），不得直接写真源。操作不存在主题 SHALL 返回未找到；标题/目标为空 SHALL 被拒绝（业务错误）。

#### Scenario: 用户直接建 track
- **WHEN** 用户提交合法的标题与学习目标
- **THEN** 系统生成 `l` 前缀递增 id 保存，默认 active，返回完整状态

#### Scenario: 分身经门禁提议建 track
- **WHEN** 分身调用 `propose("add_track", {title, goal}, reason)`
- **THEN** 生成 pending 提议且真源不变；批准后 track 才创建

#### Scenario: 空目标被拒
- **WHEN** 提交 goal 为空白字符串的 track
- **THEN** 系统拒绝并返回业务错误

### Requirement: 知识点大纲经门禁建立与调整
分身 SHALL 经门禁动作 `set_curriculum`（`track_id` + 知识点数组 `[ {title, summary?} ]`）一次性提交整份大纲，用户批准后落地。落地 SHALL 是整体替换语义：同名知识点保留其已有自评状态，新增知识点默认 `todo`，被移除的知识点连同其进度一并消失。用户亦 SHALL 能经 API 直接设置大纲（用户自己拍板不走门禁）。知识点 SHALL 有稳定 id（`k` 前缀）与学习顺序（ord）。

#### Scenario: 首次大纲落地
- **WHEN** 分身提议 `set_curriculum` 含 20 个知识点，用户批准
- **THEN** 该 track 下生成 20 个 `todo` 状态知识点，按数组顺序排列

#### Scenario: 调整大纲保留同名进度
- **WHEN** 大纲调整后再次批准，其中 3 个知识点与原大纲同名
- **THEN** 同名 3 个保留原状态，新增的为 todo，被移除的消失

#### Scenario: 未经批准不落地
- **WHEN** 分身提议 set_curriculum 而用户未处理
- **THEN** 该 track 的知识点不变，提议保持 pending

### Requirement: 自评进度
知识点状态 SHALL 为 `todo / learned / revisit` 之一。用户 SHALL 能经看板/API 直接改自评状态；分身 SHALL 只能经门禁动作 `set_point_status` 代写（用户在微信里口头自评，分身转录提议，用户批准）。AI SHALL NOT 自行判定用户掌握程度。时间戳由调用方传入，存储层不取时钟。

#### Scenario: 用户看板点「懂了」
- **WHEN** 用户对 todo 知识点点「懂了」
- **THEN** 状态变 learned，记录 learned_at

#### Scenario: 用户点「没懂」回炉
- **WHEN** 用户对 todo 或 learned 知识点点「没懂」
- **THEN** 状态变 revisit；之后可再标 learned 或退回 todo

#### Scenario: 分身代写走门禁
- **WHEN** 分身调用 `propose("set_point_status", {point_id, status}, reason)`
- **THEN** 批准前状态不变；批准后生效；AI 未经用户口头依据自行提议属流程违规，由 SOP 约束

### Requirement: 课程小结存档
课程小结（lesson note）是派生物，SHALL 经 MCP `submit_lesson_note` 直接落库，不经门禁。小结 SHALL 追加式存储（每次授课一条，不版本覆盖），记录 track、知识点标题快照、正文、来源、讲课分身。删除 track SHALL 级联删除其小结；track 下大纲调整 SHALL NOT 影响已存小结（小结不外键关联知识点）。

#### Scenario: 课后小结落库
- **WHEN** 分身讲完一课调用 submit_lesson_note
- **THEN** 小结追加保存，含知识点标题快照与正文；同知识点多次授课产生多条

#### Scenario: 大纲调整不影响历史小结
- **WHEN** 某知识点在大纲调整中被移除，但其历史小结仍在
- **THEN** 小结可查（按 track 归档），不随知识点删除

### Requirement: 下一课判定
系统 SHALL 能按序给出每个 active track 的「下一课」：优先取 ord 顺序上第一个 `todo` 知识点；若无 todo 但存在 `revisit`，返回第一个 revisit 作为回炉建议；两者皆无则该 track 视为走完。判定所用时间/数据由调用方传入，存储层不取时钟。

#### Scenario: 按序取下一课
- **WHEN** track 的知识点依次为 [A: learned, B: todo, C: todo]
- **THEN** 下一课为 B

#### Scenario: 回炉优先于新课
- **WHEN** track 无 todo 但存在 revisit 的知识点
- **THEN** 下一课返回第一个 revisit 知识点并标记为回炉

#### Scenario: 走完的 track
- **WHEN** 全部知识点均为 learned
- **THEN** 下一课为空，track 可标 done

### Requirement: 分身学习读写面
MCP SHALL 新增两个工具（9→11）：`get_learning`（读全部 active track + 知识点 + 进度 + 下一课；可按 track_id 取详情含最近小结）与 `submit_lesson_note`（课程小结直落）。契约测试的精确集合断言同步更新。MCP SHALL NOT 暴露 track/知识点/进度的直接写工具——写一律走门禁三动作（`add_track`/`set_curriculum`/`set_point_status`）。

#### Scenario: 分身备课
- **WHEN** 用户在微信说「今天上课」，分身调用 get_learning
- **THEN** 返回各 track 与下一课信息，分身取下一课内容开讲

#### Scenario: MCP 无学习直写工具
- **WHEN** 检查 MCP 工具集合
- **THEN** 不存在 add_track/set_curriculum/set_point_status 名字的直写工具，三者仅作为 propose 的 action 存在

### Requirement: 看板「讲武」tab
看板 SHALL 新增「讲武」tab：track 卡片展示标题、目标、进度（learned/total）、下一课、自评操作入口；展开可见知识点清单（每项可点 懂了/没懂/重置）与课程小结历史（正文转义渲染 + 来源链接，样式复用回答视图）。界面 SHALL NOT 使用装饰性 emoji（沿用既有要求）。

#### Scenario: 看板查看进度
- **WHEN** 用户打开「讲武」tab
- **THEN** 每个 active track 显示 learned/total 进度与下一课标题

#### Scenario: 看板自评
- **WHEN** 用户在某知识点点击「懂了」
- **THEN** 状态即时更新并刷新进度显示

#### Scenario: 来源链接安全渲染
- **WHEN** 课程小结含来源列表（模型生成内容）
- **THEN** 仅 http(s) 协议可点击，属性经转义（复用 escAttr/safeUrl）

### Requirement: 部署前提与教学入口
本能力的运行前提 SHALL 是：分身经 stdio 接同机 deputy（不变）；上课入口为微信对话（OpenClaw），看板为成绩单。学习由进度驱动、用户发起，SHALL NOT 引入定时调度。教学素材 SHALL 按以下次序取用：①分身自身知识（主体）→ ②互联网检索（龙虾侧自身能力，deputy 不集成）→ ③feed-curator 语料仅作部分佐证（讲前沿话题时引用）。deputy 不强制来源，但小结 SHALL 如实声明素材来源。

#### Scenario: 语料不可用不阻塞授课
- **WHEN** feed-curator 不可用，用户请求上课
- **THEN** 分身照常授课（自身知识/互联网），小结声明「本课未引用本地语料」
