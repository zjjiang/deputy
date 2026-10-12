# preset-questions Specification

## Purpose

预设问题：用户预设「要 AI 持续关注什么」，常驻 AI 分身定期基于 feed-curator 知识库思考并回填版本化回答，看板阅读。让沉淀的订阅信息以「增量回答」的方式反哺每日决策，回答与问题的进化都尊重「人类做门禁」。


## Requirements
### Requirement: 用户管理预设问题
用户 SHALL 能在看板/HTTP API 创建、编辑、删除预设问题。问题包含：标题、prompt（给 AI 的完整问题文本）、过滤器（`kinds`/`domain` 为 feed-curator 侧的文档类型与领域，deputy 不拥有该分类法，SHALL 只做类型检查、按不透明值透传，不校验取值；`days` 时间窗天数、`max_docs` 单次取料上限，均为正整数）、节奏 `cadence` ∈ {daily, weekly, manual}。非法取值 SHALL 被拒绝并返回业务错误（HTTP 400）；操作不存在的问题 SHALL 返回未找到（HTTP 404）。

#### Scenario: 创建一个每日问题
- **WHEN** 用户提交合法的标题、prompt、过滤器和 `cadence=daily`
- **THEN** 系统生成 `q` 前缀的递增 id 保存问题，默认 `active`，返回创建后的问题完整状态

#### Scenario: 非法节奏被拒
- **WHEN** 用户提交 `cadence=hourly`（不在 {daily, weekly, manual} 中）
- **THEN** 系统拒绝创建并返回 400，不产生任何数据

#### Scenario: 编辑不存在的问题
- **WHEN** 用户对不存在的 id 提交编辑或删除
- **THEN** 系统返回 404，不产生任何数据

#### Scenario: 删除问题级联清理回答
- **WHEN** 用户删除一个已有历史回答的问题
- **THEN** 该问题的全部回答一并删除

### Requirement: 到期判定
问题 SHALL 按以下规则判定「到期」（需要分身运行）：仅 `active` 的问题可到期；满足以下任一条件即到期——从运行过但距今超过节奏周期（daily 1 天、weekly 7 天，达到即算超）、从未运行过、或存在手动请求标记。手动请求标记 SHALL 无视 last_run 时间使问题立即到期；`inactive` 的问题 SHALL 永不到期。到期判定所用时间由调用方传入，存储层不得自行取时钟。

#### Scenario: 从未运行的问题到期
- **WHEN** 一个 active 的 daily 问题创建后从未有过回答
- **THEN** 它被判定为到期

#### Scenario: 当天已运行的 daily 问题不到期
- **WHEN** 一个 active 的 daily 问题距今不足 1 天前刚运行过，且无手动请求标记
- **THEN** 它不被判定为到期

#### Scenario: weekly 恰满 7 天即到期
- **WHEN** 一个 active 的 weekly 问题上次运行距今恰好 7 天
- **THEN** 它被判定为到期

#### Scenario: inactive 的问题永不到期
- **WHEN** 一个问题被停用（inactive），无论隔多久
- **THEN** 它不出现在到期集合中

#### Scenario: 手动请求使 manual 问题立即到期
- **WHEN** 用户对一个 `cadence=manual` 且从未到期过的问题点「跑一次」
- **THEN** 该问题立即被判定为到期

### Requirement: 回答版本化存档
回答 SHALL 直接落库，不经过门禁队列。对同一问题同一天的每次提交 SHALL 存为一个**新版本**（版本号按同题同日递增），提交时同日旧版本 SHALL 被标记为 `superseded`（保留可查，不再是当前结论），最新版本即当前结论。版本化使回答随知识库同日新增内容而进化。分身对不存在的问题提交 SHALL 得到未找到错误；对已停用的问题提交 SHALL 被拒绝（业务错误）；空正文 SHALL 被拒绝。提交成功 SHALL 同步更新问题的 last_run 时间并清除手动请求标记（同一事务）。

#### Scenario: 同日第二次提交产生 v2
- **WHEN** 某问题当天已有 v1 回答，分身再次提交（如午后新料进库）
- **THEN** 系统新增 v2，v1 被标记为 superseded 且内容仍可查，v2 为当前结论

#### Scenario: 提交成功推进问题状态
- **WHEN** 分身提交回答成功
- **THEN** 该问题的 last_run 更新为提交时间，手动请求标记被清除，且这两项与回答写入在同一事务中生效

#### Scenario: 对不存在或已停用的问题提交
- **WHEN** 分身对不存在的 id 提交回答
- **THEN** 返回未找到错误；对已停用的问题提交则返回业务错误，两者都不产生回答

#### Scenario: 空正文被拒
- **WHEN** 分身提交正文为空（或全空白）的回答
- **THEN** 系统拒绝并返回业务错误，不产生新版本

### Requirement: 回答的用户操作
用户 SHALL 能在看板阅读回答、标记已读、删除单条回答。已读/删除 SHALL 仅影响被操作的回答本身，不影响同题其他版本。

#### Scenario: 标记已读只影响该条
- **WHEN** 用户把 v1 标记为已读
- **THEN** v1 状态变为已读，其他版本状态不变

#### Scenario: 删除单条回答
- **WHEN** 用户删除 v2
- **THEN** v2 消失，v1（superseded）仍在；删除不存在的回答返回 404

### Requirement: 分身读题与历史回答
分身 SHALL 能经 MCP 获取到期问题（默认仅到期题，可切换全部），返回内容含完整 prompt、解析后的过滤器、节奏与到期原因（首次运行 / 超周期 / 手动请求）。分身 SHALL 能经 MCP 读取单题详情及其**最近若干条回答（各日最新版本）**，作为增量回答的依据——新回答 SHOULD 表达「与上期相比的变化」而非重复历史内容。

#### Scenario: 取到期题
- **WHEN** 分身调用到期题列表接口
- **THEN** 仅返回到期的问题，每条含 prompt、过滤器（解析后的结构）、cadence 与到期原因

#### Scenario: 读历史回答支撑增量
- **WHEN** 分身读取某问题详情并请求最近回答
- **THEN** 返回近期各日的最新版本回答（不含 superseded 旧版），分身据此产出增量回答

### Requirement: 分身经门禁提议建题/改题
`add_question` 与 `edit_question` SHALL 加入门禁动作白名单：分身只能经 `propose` 提议，用户批准后系统才派发执行，驳回不执行。提议必须附理由；参数缺失或非法取值在批准派发时被业务规则拦截，提议保持待批。MCP 层 SHALL NOT 暴露直接创建/修改问题的工具（真源配置写操作只走门禁）。

#### Scenario: 分身提议新建问题
- **WHEN** 分身调用 `propose("add_question", {title, prompt, cadence, ...}, reason)`
- **THEN** 生成一条 pending 提议且问题未创建；用户批准后问题才真正创建

#### Scenario: 批准非法参数的提议被拦截
- **WHEN** 用户批准一条 cadence 非法的 add_question 提议
- **THEN** 派发被业务规则拒绝，提议保持 pending，问题未创建

#### Scenario: MCP 无直写题工具
- **WHEN** 检查 MCP 工具集合
- **THEN** 不存在名为 add_question / edit_question 的直接写工具，二者仅作为 propose 的 action 存在

### Requirement: 看板「问题」tab
看板 SHALL 新增「问题」tab：问题列表展示标题、prompt 摘要、节奏、上次运行时间、到期徽标与未读数；提供「跑一次」（打手动请求标记）与编辑/删除/停用入口；点开问题按需加载历次回答，正文渲染含版本号与 confidence 标识，旧版本标注 superseded，回答附来源链接列表与标已读/删除操作。界面 SHALL NOT 使用装饰性 emoji（沿用既有要求）。

#### Scenario: 看板展示与手动触发
- **WHEN** 用户打开「问题」tab 并点击某题的「跑一次」
- **THEN** 该题立即带到期标识，下一次分身轮询会取走它

#### Scenario: 回答列表展示版本
- **WHEN** 某题当天有 v1（superseded）与 v2（当前）
- **THEN** 回答视图以 v2 为当前内容展示，v1 可展开查看且带版本与 superseded 标识

#### Scenario: 来源链接安全渲染
- **WHEN** 渲染回答的来源列表（内容来自模型生成）
- **THEN** 仅 http(s) 协议的链接可点击，属性经 HTML 转义，注入内容不生效

### Requirement: 时钟与 run_date 约定
回答/问题的时间戳（created、last_run、requested 等）SHALL 使用 UTC ISO 格式并由调用方传入，存储层不取时钟。回答的 `run_date`（「哪一天的题」，版本分组依据）SHALL 为东八区日历日（YYYY-MM-DD），由 API/MCP 边界层计算并显式传入。

#### Scenario: 深夜提交归入正确日期
- **WHEN** 东八区时间 7 月 24 日 07:00（UTC 为 23 日 23:00）分身提交回答
- **THEN** 该回答的 run_date 为 2026-07-24，与当天更早版本构成同日版本序列

### Requirement: 部署前提
本能力的运行前提 SHALL 是：分身经 stdio 接入**同机**的 deputy 实例（分身、feed-curator、deputy 同机部署）。本能力 SHALL NOT 引入远程传输或对外的 MCP/API 监听地址变更——若未来分身改为远程接入，必须先按红线补齐鉴权，属独立变更。

#### Scenario: 当前部署形态
- **WHEN** 按本能力部署（mini 上的分身经 stdio 接同机 deputy）
- **THEN** 不涉及任何网络暴露面的扩大，鉴权红线不被触碰
