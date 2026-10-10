## Why

信息存而不读：feed-curator 已沉淀 3057 篇 article/paper/repo（正文全量），但收藏/阅读动作几乎为零，AI 摘要从未跑过——人消化不过来，信息没有产出决策价值。与其让人去找信息，不如让用户**预设问题**，由常驻 AI 分身定期基于知识库思考，把带引用来源的回答主动送到看板，让存量的信息开始反哺每日决策。

## What Changes

- 新增「预设问题」能力：用户在看板创建问题（标题 + prompt + 过滤器 `kinds/domain/days/max_docs` + 节奏 `daily/weekly/manual`），看板新增「问题」tab 展示问题与历次回答
- MCP 分身接口新增 3 个工具（6→9）：`list_questions`（取到期题，含过滤器与到期原因）、`get_question`（读题详情 + 最近 N 条回答，支撑**增量回答**）、`submit_answer`（回填回答，唯一的 answers 写入口）
- **回答直接落库，不过门禁**：回答是对用户预设之问的派生产物，不是对项目真源（projects/todos/backlog/focus）的写操作；看板可读、标已读、删除
- **回答版本化（append-only）**：同题同日每次提交都存为新版本（v1/v2/v3…），新版本落地时同日旧版自动标记 `superseded`（保留可查，最新版为当前结论）。当日内新料进库后分身可再跑出新版本，实现回答随知识库**自进化**；重试产生的近重复版本无害，看板永远展示最新版
- **门禁白名单新增 `add_question` / `edit_question`**：分身跑题跑出心得可提议新建/调整问题，用户在门禁批准后才生效——问题自身的「自进化」也走人类门禁
- 手动触发：看板「跑一次」给问题打 requested 标，分身轮询取走；取题不写 last_run_at（分身崩溃可自愈重跑）
- 新增 `docs/thinking-sop.md`：分身跑题 SOP（两轮硬预算 / 句级引用 / 无料日降级 / 增量回答）+ OpenClaw cron prompt 模板
- CLAUDE.md 红线①措辞精确化（真源范围 + answers 例外）；前端 `esc()` 补引号转义 + 来源 `href` 仅放行 http(s)（XSS 防御）
- 部署前提写进 spec：分身经 stdio 接**同机** deputy 实例，本 change 不引入远程传输/鉴权改动（红线④不触碰）

## Capabilities

### New Capabilities

- `preset-questions`: 预设问题的定义与校验、到期判定规则、回答版本化存档（append-only，同日多版本、superseded 标记）、增量回答（回答感知历史）、分身经门禁提议建题/改题、看板「问题」tab 展示、部署前提（分身同机 stdio 接入）

### Modified Capabilities

- （无——现有 `project-management` 的 requirement 均不变；「界面不使用装饰性 emoji」要求自动覆盖新 tab）

## Impact

- **代码**：`app/domain.py`（cadence 常量 + 白名单 +1 条目×2）、`app/store/db.py`（SCHEMA 追加 questions/answers 两表，幂等建表无迁移）、`app/store/questions.py`（新建 store 模块）、`app/store/proposals.py`（approve 派发扩展到 questions 的动作）、`app/api.py`（约 9 个端点）、`app/mcp_server.py`（3 个新工具 + docstring）、`app/web/index.html`（新 tab + esc 加固）、`docs/thinking-sop.md`（新）、`CLAUDE.md`
- **测试**：`tests/test_questions_store.py`、`tests/test_questions_api.py`（新建）；`tests/test_mcp_contract.py`（工具精确集合 6→9 + 分身视角端到端）；`tests/test_gate.py`（add_question/edit_question 门禁用例）
- **依赖**：无新增（`zoneinfo` 为标准库）
- **数据**：`data/deputy.db` 新增两表（`CREATE TABLE IF NOT EXISTS`，对现有数据零影响；`data/` 已 gitignore，数据不出墙）
- **部署**：使用入口为 Mac mini 上的 deputy 实例（分身、feed-curator 同机）；Air 本地实例仅开发用。运维前置：mini 上 feed-curator 服务在跑；建议配 `DEEPSEEK_API_KEY` 跑一轮 analyze（不配也能跑，分身直接读原文）
- **破坏性**：无（纯新增能力；MCP 工具集合扩大属预期演进，契约测试同步更新）
