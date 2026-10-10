## Context

现状：deputy 是纯真源 + 门禁（projects/todos/backlog/focus 四表 + proposals 队列），零外部依赖、零调度器、零 LLM 集成；分身经 stdio 接同机 MCP（6 工具）。运行拓扑：分身（OpenClaw/龙虾/dodo）与 feed-curator 服务、deputy 实例同在 Mac mini。相关调研结论见 proposal 与 `docs/thinking-sop.md` 引用的 deep research 模式（两轮硬预算 / 句级引用 / 无料日降级）。

## Goals / Non-Goals

**Goals**
- deputy 侧只做「问题配置 + 版本化回答存档 + MCP 取题/回填」，思考与取料完全留给分身
- 回答 append-only 版本化，同日可进化（v1→v2），历史可溯
- 分身可提议建题/改题（走既有门禁机制），题目进化不破「人类做门禁」

**Non-Goals**
- 不动 feed-curator（搜索能力缺口由它自己的 OpenSpec change 解决）
- deputy 内不做任何 LLM 调用、调度器、cron；不引入远程传输/鉴权改动（红线④）
- 不做向量/语义检索、多轮 deep research 循环、双分身 claim/lease 防重
- 分身不提议删除/停用问题（用户专属动作；后续需要再加 `remove_question` 动作）

## Decisions

**D1 部署/传输前提：分身同机 stdio 接入，不碰红线④**
分身与 deputy 实例同机（mini），MCP 走现有 stdio 传输，零网络暴露面变化。备选「HTTP/SSE 远程接入」被否：需先做鉴权，超出本 change，且当前拓扑不需要。spec 已把此前提固化为 Requirement，防止未来分身挪机时无声破线。

**D2 时钟约定：UTC aware 时间戳 + 东八区 run_date，边界层供时**
`created/requested_at/last_run_at` 沿用 `_now()` 的 UTC ISO 先例；`run_date` 是「哪一天的题」（版本分组键），按东八区日历日（`zoneinfo` Asia/Shanghai）在 API/MCP 边界算好显式传入。备选「run_date 用 UTC 日期」被否：东八区早上 8 点前的回答会被记成昨天，违背直觉。store 仍不取时钟（红线③），所有时间可注入 → 到期逻辑完全可测。

**D3 回答 append-only 版本化，而非同日覆盖**
`answers` 无 UNIQUE 约束，每次提交插入新行，`version` = 同题同日 max+1，同事务把同日旧行置 `superseded`。备选「UNIQUE + ON CONFLICT 覆盖」被否：销毁旧结论、已读状态连带丢失，且与 proposals 的 append-only 哲学相悖。代价：分身崩溃重试会产生近重复版本——接受（SOP 约束「仅在确有新料/新结论时提交」，看板永远展示最新版，噪音无害）。单用户场景不做版本合并/去重。

**D4 门禁派发归位：questions 自带 _DISPATCH，approve 按 action 归属路由**
新增动作 `add_question`/`edit_question` 的写函数与派发表在 `app/store/questions.py`；`proposals.approve` 按 action 归属派发（`questions.handles(action)` 判定），questions.dispatch 与 projects.dispatch 同构（`inspect.signature` 探测 `now` 参数的做法照抄）。备选「把题目动作塞进 projects._DISPATCH」被否：跨模块耦合，projects 不该知道 questions。`propose()` 的必填键校验沿用 `PROPOSAL_ACTIONS` 白名单即可——`add_question` 必填 `title/prompt`、`edit_question` 必填 `question_id`，其余键（cadence/filter 等）天然免检，无需动可选键豁免表。

**D5 submit 边界行为：不存在 → KeyError(404)，停用 → DomainError(400)，空正文 → DomainError**
停用意味着用户明确不想再要回答，拒收并让分身放弃；不存在照 `_require_project` 的 KeyError 措辞。提交与「推进 last_run_at + 清 requested_at」在同一写事务，避免「答了但题还挂着」的重复跑。

**D6 取题不写 last_run_at**
到期判定只读；`last_run_at` 仅在 submit 成功时推进。分身取题后崩溃时题目仍到期，下轮重跑自愈。备选「取题即占位」被否：需要 claim/lease 机制，单用户规模属过度设计。

**D7 MCP 工具集：6 → 9**
新增 `list_questions(all=False)`（默认仅到期题，返回解析后 filter、cadence、due 原因）、`get_question(id, with_answers=3)`（题详情 + 近 N 日最新版回答，支撑增量回答）、`submit_answer(...)`（唯一 answers 写入口；run_date 缺省按东八区算）。契约测试的精确集合断言同步扩到 9；`test_mcp_has_no_direct_write_tools` 的黑名单来自 `PROPOSAL_ACTIONS`，`add_question/edit_question` 自动入黑名单（无重名冲突）。

**D8 API payload：列表带聚合不带正文，回答按需分页**
`GET /api/questions` 每题附 `unread_count`（仅最新版本计 unread，superseded 不计）、`last_answer_at`、最新版 ~120 字预览、`due`；正文只在 `GET /api/question/{id}/answers?limit=30` 拉取（5s 轮询 payload 可控）。端点风格：`/api/question/{id}/...` 与 `/api/answer/{id}/read|delete` 路径式，照 `/api/project/{id}/archive` 先例。

**D9 前端安全：esc 补引号转义 + href 协议白名单**
`sources` 是模型生成内容，现有 `esc()` 不转义 `"`，直接拼 `<a href>` 会属性逃逸。新增 `escAttr()`（转义 `"` 与 `'`），href 仅放行 `http(s):`。回答正文用 pre-wrap 转义渲染（不引 markdown 库，保持单文件零依赖；行内 `[doc_id]` 引用以纯文本呈现，语义由 sources 列表承载）。

**D10 SOP 与 cron prompt 放 deputy 仓库 docs/，执行配置在 mini**
`docs/thinking-sop.md` 是给分身看的操作规范（取料 → 初答自检 confidence+gaps → 至多一次补料 → 定稿；无料日降级；增量回答规则；版本提交纪律），OpenClaw cron 的 prompt 模板附在其中。deputy 代码不含任何调度逻辑；mini 侧配置属运维步骤，写进 PR 描述与 SOP 顶部。

## Risks / Trade-offs

- [分身不按 SOP 跑（多版本刷屏/编造引用）] → SOP 写死提交纪律与引用规则；看板可删；confidence/gaps 元信息让坏产出可识别
- [同日版本爆炸（cron 误配高频）] → list_questions 默认只回到期题，cron 正常节奏下同日最多 2-3 版；UI 折叠旧版本
- [filter 里 domain 等字段与 feed-curator 语义漂移] → store 按不透明字符串透传不校验（D8/spec），语义由分身与 feed-curator 之间维护
- [questions/answers 增大 deputy.db] → 单用户量级（十题、日均几条）远未到瓶颈；answers 带 (question_id, run_date, version) 索引
- [东八区/UTC 双口径增加理解成本] → D2 已把口径写死进 spec，实现处（边界层）集中在 api.py/mcp_server.py 各一处

## Migration Plan

纯新增：`SCHEMA` 追加两表 `CREATE TABLE IF NOT EXISTS`，`init_db` 幂等执行，对既有数据零影响，无迁移步骤。回滚 = revert 分支（新表残留无副作用，可手动 DROP 或留置）。

## Open Questions

无——部署/时钟/版本化/边界行为四个关键决策已在本文件定死并反映进 spec。
