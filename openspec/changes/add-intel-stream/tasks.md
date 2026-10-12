## 1. feed-curator 配套（其仓库，独立 PR）

- [x] 1.1 feed-curator change `add-docs-star-sort`：`GET /api/docs` 增 `sort=time|stars`（复用 `_latest_ok_analysis_ids`）与 `min_stars`（1-5）参数 + 测试；validate 通过（在其仓库分支提 PR）

## 2. curator 客户端（TDD：Red → Green）

- [x] 2.1 写 `tests/test_curator.py`（Red，httpx.MockTransport 三态）：list_docs 转发参数与响应透传、domains、set_reading、超时/非 200/连接错误 → CuratorUnavailable；跑确认全红
- [x] 2.2 写 `app/services/curator.py`（Green）：唯一集成出口（base URL env 可配默认 127.0.0.1:9003、timeout 2.0、CuratorUnavailable 异常）；`pyproject.toml` httpx 进主依赖；跑 `pytest tests/test_curator.py` 全绿

## 3. 代理端点（TDD：Red → Green）

- [x] 3.1 写 `tests/test_intel_api.py`（Red）：`GET /api/intel/docs`（page→offset、筛选透传、正常透传 JSON）、`GET /api/intel/domains`、`POST /api/intel/reading/{doc_id}`；CuratorUnavailable → 503 带降级文案；参数校验（min_stars 越界 400）；跑确认全红
- [x] 3.2 `app/api.py`（Green）：三端点 + `_guard` 风格异常映射；跑 `pytest tests/test_intel_api.py` 全绿

## 4. 前端

- [ ] 4.1 `app/web/index.html`：军情 tab 双区（奏折区挂分区标识逻辑不动；情报流区：筛选条（领域下拉/类型/仅四星/排序）/卡片列表（类型/领域/星级/摘要/已读收藏标识与按钮）/分页；`window._intel` 自持筛选与页码；降级卡 + 重试；不进 5s 轮询）；复用既有样式与 escAttr/safeUrl；自查无装饰性 emoji
- [ ] 4.2 本地 smoke：起 feed-curator（本机）+ deputy → 军情 tab 情报流拉到真实数据 → 筛选/翻页/已读收藏写回 → 杀 feed-curator 看降级卡与奏折无恙 → 重启恢复；XSS 回归

## 5. 文档与收尾

- [ ] 5.1 CLAUDE.md 章程：军情处三模式（奏折/面圣/翻阅）+ 集成出口约定（HTTP 访问只经 curator 模块、代理不存储）；mcp_server docstring 军情处描述同步
- [ ] 5.2 全量回归：`uv run pytest -q` 全绿（MCP 契约 11 工具不动）；`openspec validate add-intel-stream` 通过
