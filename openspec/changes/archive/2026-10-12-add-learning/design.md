## Context

deputy 现有作战处（projects/todos/backlog/focus）与军情处（questions/answers，preset-questions 已归档）。门禁白名单 15 个动作、MCP 工具 9 个、派发已按 store 模块归属路由（projects/questions）。feed-curator 侧 `add-corpus-search`（jieba+BM25，`search_docs`/`get_doc` MCP）即将完工，为教学取料就绪。教学强度经探索定为中档：路线 + 讲解 + 自评，不做 AI 考试。课堂在微信（OpenClaw），看板是成绩单。

## Goals / Non-Goals

**Goals**
- deputy 补上学习账本：大纲真源（门禁保护）+ 自评进度 + 课程小结存档
- 学习循环全部复用既有骨架：门禁三动作照 add_question 套路、小结直落照 submit_answer 套路、看板视图照「军情」tab 套路
- 下一课判定（todo 优先、revisit 回炉）让"今天学什么"零思考成本

**Non-Goals**
- AI 考试/掌握度评定（重档内容，明确砍掉）
- SM-2/间隔重复调度（进度驱动 + 用户发起，不引入定时；未来需要走军情处同款 cron 思路另立）
- 讲义长文存储——讲解发生在微信对话，deputy 只存课后小结
- 多用户/多学员；feed-curator 侧任何改动

## Decisions

**D1 部署前提与课堂形态：同机 stdio 不变，课堂在微信**
与 preset-questions 的 D1 同款红线考量：不引入远程传输。上课入口是微信对话（OpenClaw），deputy 不承载对话本身，只存小结——讲义长文不入库是刻意裁剪。

**D2 三张表 + 小结不外键知识点**
`learning_tracks`（l{n}）/ `knowledge_points`（k{n}，FK track ON DELETE CASCADE）/ `lesson_notes`（INTEGER 自增，FK track 级联，但**不外键知识点**——存 `point_title` 标题快照）。理由：`set_curriculum` 整体替换会增删知识点，小结若外键知识点会被连带清掉；学习历史比大纲更珍贵。备选「外键 + ON DELETE SET NULL」被否：标题快照查询更直观，且无需改知识点删除语义。

**D3 大纲语义：整体替换 + 同名继承状态**
`set_curriculum(track_id, points[])` 落地时替换该 track 全部知识点，按 `title` 精确匹配继承原状态（learned/revisit 保留），新增默认 todo。备选「仅允许首次、调整走逐点增删」被否：分身重排/补全大纲是一次性心智动作，逐点编辑门禁噪音太大；同名继承保住了"调整大纲不清进度"的底线。替换语义在 propose 阶段就明示用户（reason 必填承担告知义务）。

**D4 门禁三动作，进度代写哲学**
`add_track(title, goal)` / `set_curriculum(track_id, points)` / `set_point_status(point_id, status)` 进 `PROPOSAL_ACTIONS`，派发经 `learning.handles()` 路由（复用 questions 模式）。进度是用户自评：AI 不自行判定掌握——微信里用户说"懂了"，分身也只能提议代写、用户批准。备选「分身直写进度（用户口头即授权）」被否：红线 1 刚精确化，不再开直写口子；一次门禁点击的摩擦换状态记录的确定性，值。

**D5 状态机：todo/learned/revisit，无更多状态**
`todo → learned | revisit`；`revisit → learned | todo`。learned 可打回 revisit（温习时发现没真懂）。不引入 in-progress 之类中间态——"正在学"由下一课判定隐式表达（todo 队首就是正在学的）。

**D6 下一课判定放 store 层纯函数**
`next_point(track)`: ord 序第一个 todo；无 todo 取第一个 revisit（回炉）；皆无 → None（可标 done）。无时间因素，纯数据规则，完全可测。

**D7 MCP 9→11：只读 + 直落各一**
`get_learning(track_id?)`：默认返回全部 active track（含知识点、进度计数、下一课），传 track_id 则附最近小结——分身备课唯一入口。`submit_lesson_note(track_id, point_title, body_md, sources?, model?)`：小结直落，提交纪律写 docstring（指向 docs/teaching-sop.md）。契约测试精确集合同步。

**D8 API 面与前端**
端点：`GET /api/learning`（track 概览+进度）、`GET /api/learning/{id}`（详情含 notes）、`POST /api/learning/track/add|{id}/edit|{id}/remove|{id}/status`（生命周期）、`/api/learning/track/{id}/curriculum`（用户直接设大纲）、`POST /api/point/{id}/status`。前端「讲武」tab 照「军情」tab 模式：卡片 + 进度条（learned/total）+ 知识点三键自评（懂了/没懂/重置）+ 小结历史复用回答视图样式（escAttr/safeUrl 已就位）。

**D9 教学 SOP 落 docs/teaching-sop.md**
上课流程（get_learning 取下一课 → 讲解 → 引导自评 → set_point_status 代写提议 → submit_lesson_note 存档）、素材次序（**自身知识 → 互联网 → feed-curator 部分佐证**：课本型知识靠自身，互联网补新，语料只在讲前沿话题时引用——与军情处的「强依赖语料」刻意相反，两处素材边界由此区分）、没懂回炉处理、小结规范（一课一条、含要点回顾与**素材来源声明**）。OpenClaw 侧无 cron（进度驱动），对话入口说明写 SOP 顶部。

## Risks / Trade-offs

- [大纲质量差（知识点粒度不合适）] → 门禁批准环节用户把关；set_curriculum 可反复调整，同名继承保证试错成本低
- [微信代写忘记批准，进度挂起] → pending 提议在看板门禁区可见；SOP 要求分身代写后提醒用户去批
- [同名匹配继承状态，改名即丢状态] → 接受；SOP 提示分身调整大纲时尽量保持已学知识点标题不变
- [小结刷屏] → 一课一条、追加式，量级天然小（几十个知识点 × 复习次数）
- [三个模块 tab 挤满导航] → 配套 rebrand change 做 tab 分组（作战/军情/讲武）

## Migration Plan

纯新增：SCHEMA 追加 3 表幂等执行，无迁移。回滚 = revert 分支，残留表无副作用。

## Open Questions

无——教学强度（中档）、课堂形态（微信+看板成绩单）、门禁边界（三动作）均已在探索阶段与用户对齐。
