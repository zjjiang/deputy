## 1. Store 层（TDD：Red → Green）

- [x] 1.1 写 `tests/test_questions_store.py`（Red）：CRUD/id 生成 q1,q2/ord 递增、title/prompt 空 → DomainError、非法 cadence → DomainError、filter 非法类型 → DomainError、filter 返回解析后 dict（后修正：kinds/domain 属 feed-curator 分类法，只查类型不查取值，见 spec 与 design D2 注）；跑 `uv run pytest -q tests/test_questions_store.py` 确认全红
- [x] 1.2 同文件补到期矩阵用例（Red）：active+从未跑→到期；daily 当天已跑→不到期；weekly 恰 7 天→到期；inactive 永不到期；manual 无请求→不到期；requested 非空无视 last_run_at；固定 NOW 常量注入
- [x] 1.3 同文件补 submit/版本化用例（Red）：首提 v1；同日再提 v2 且 v1 变 superseded 保留可查；跨日重新从 v1 计；提交后 last_run_at 更新+requested_at 清空（同事务）；空正文→DomainError；不存在→KeyError；停用→DomainError；remove 级联删 answers；标已读只影响单条；删不存在→KeyError
- [x] 1.4 `app/domain.py`：加 `VALID_CADENCES`/`CADENCE_PERIODS`/cadence 标签/answer 状态常量，`PROPOSAL_ACTIONS` 加 `add_question`、`edit_question`；跑 store 测试仍红（函数未实现）确认白名单不破坏现有 gate 测试
- [x] 1.5 `app/store/db.py`：SCHEMA 追加 questions/answers 两表（含 version 列、(question_id,run_date,version) 索引）（可选键豁免表无需扩展——不在 required 元组的键天然免检，见 design D4 修正）；跑 `uv run pytest -q` 确认除新用例外无回归
- [x] 1.6 写 `app/store/questions.py`（Green）：add/edit/remove/list_questions(now)/get_question/request_run/list_answers/mark_answer_read/delete_answer/submit_answer + questions._DISPATCH，到期判定与版本化按 spec；跑 `uv run pytest -q tests/test_questions_store.py` 全绿
- [x] 1.7 `app/store/proposals.py`：approve 按 action 归属派发（projects 或 questions 的 dispatch）；`tests/test_gate.py` 补用例：propose("add_question") → 真源未变且 pending+1；approve 后问题创建；cadence 非法时 approve 被拦保持 pending；reject 不创建；跑 `uv run pytest -q tests/test_gate.py` 全绿

## 2. API 层（TDD：Red → Green）

- [x] 2.1 写 `tests/test_questions_api.py`（Red）：GET /api/questions 聚合字段（unread_count 仅最新版计数/last_answer_at/预览/due）；question add/edit/remove/run、answers?limit、answer read/delete 的 200 路径；非法 cadence→400；不存在→404；run 后 store 里 requested_at 生效；跑确认全红
- [x] 2.2 `app/api.py`（Green）：9 个端点 + Pydantic body 类 + `_guard` 转发；边界层 `zoneinfo` 算 run_date（Asia/Shanghai）与 UTC now；跑 `uv run pytest -q tests/test_questions_api.py` 全绿

## 3. MCP 层（TDD：Red → Green）

- [x] 3.1 `tests/test_mcp_contract.py`：精确集合断言更新为 9 工具（+list_questions/get_question/submit_answer）（Red）；补分身视角端到端：list_questions 取到到期题 → submit_answer → get_question 的最近回答可见（Red）；确认 `test_mcp_has_no_direct_write_tools` 对新白名单自动生效且绿
- [x] 3.2 `app/mcp_server.py`（Green）：三个新工具 + docstring（到期语义/增量回答/提交纪律摘要，指向 docs/thinking-sop.md）；submit_answer 的 run_date 缺省按东八区算；跑 `uv run pytest -q tests/test_mcp_contract.py` 全绿

## 4. 前端

- [x] 4.1 `app/web/index.html`：`escAttr()`（转义引号）+ href 仅放行 http(s)；TABS 加「问题」+ renderQuestions()（列表卡片：标题/prompt 摘要/节奏/上次运行/到期徽标/未读数/「跑一次」/编辑/删除/停用）+ 按需加载回答（版本徽标/superseded 折叠/confidence 标识/来源链接/标已读/删除）；load() 的 Promise.all 并入 /api/questions；自查界面无装饰性 emoji
- [x] 4.2 本地 smoke：`uv run uvicorn app.api:app --port 8899` → 建题 → 「跑一次」→ 脚本以 store 身份 submit v1+v2 → 看板显示 v2 当前/v1 折叠/未读数正确；来源带 javascript: 的链接不可点击（手工验证 XSS 防御）

## 5. 文档与收尾

- [x] 5.1 写 `docs/thinking-sop.md`：分身跑题 SOP（取料→初答自检→至多一次补料→定稿；无料日降级；增量回答规则；版本提交纪律）+ OpenClaw cron prompt 模板 + mini 侧运维前置（feed-curator 服务、可选 DEEPSEEK key + analyze）
- [x] 5.2 CLAUDE.md：红线①措辞精确化（真源=projects/todos/backlog/focus；answers 为派生物走专属工具）+ 架构速览 store 清单加 questions.py + 标语加 answers 例外；`app/mcp_server.py` 模块 docstring 同步
- [x] 5.3 全量回归：`uv run pytest -q` 全绿（38 旧 + 新增用例，含 9 工具契约与守门测试）；`openspec validate add-preset-questions` 通过
