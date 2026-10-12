## Why

军情处目前只有「奏折」（预设问题的定时/手动简报）一个被动面。用户需要**主动看情报**：在军情处里直接翻阅语料流——四星文章、各领域的论文/仓库/文章——而不必切到 feed-curator 的页面。数据侧已就绪：feed-curator `GET /api/docs` 的响应自带 stars/summary/domains/已读收藏状态（total 分页齐全），`POST /api/docs/{id}/reading` 可写回阅读状态。缺的是 deputy 侧的呈现与转发。经用户确认采用**内嵌方案（B）**：deputy 首次引入对 feed-curator 的 HTTP 客户端（localhost、读为主 + 阅读状态代理写回），奏折与情报流在同一「军情」tab 呈现。

## What Changes

- 新增军情处「翻阅」能力：deputy 后端代理 feed-curator 的文档流（领域/类型/仅四星/分页筛选），前端「军情」tab 改为**双区布局**——奏折区（现有）+ 情报流区（新）
- 新增 curator 客户端模块（唯一集成出口）：拉流、领域列表、阅读状态写回代理；localhost 限定、超时与降级（图书馆闭馆提示，奏折区不受影响）
- **状态归属不破**：已读/收藏的存储仍在 feed-curator `reading` 表，deputy 只做渲染与代理写回（转 `POST /api/docs/{id}/reading`），不落任何库
- 配套 feed-curator 侧小改（其仓库独立 change `add-docs-star-sort`）：`GET /api/docs` 增 `sort=stars` 与 `min_stars` 参数（复用网页版现成查询逻辑）；未合入前情报流退化为时间序、隐藏四星门槛按钮
- 章程更新：军情处两模式 → **奏折 / 面圣 / 翻阅** 三模式
- MCP 面零变更（分身取料走 feed-curator 自己的 MCP，不经 deputy 转发）

## Capabilities

### New Capabilities

- `intel-stream`：军情处语料浏览面——curator 客户端与降级、代理端点、情报流筛选与分页、阅读状态代理写回、双区布局、部署前提

### Modified Capabilities

- 无（preset-questions 的奏折 requirement 不变；军情 tab 新增分区属新能力）

## Impact

- **代码**：`app/services/curator.py`（新，唯一集成出口）、`app/api.py`（`/api/intel/*` 代理端点 ×3）、`app/web/index.html`（军情 tab 双区）、`pyproject.toml`（httpx 进运行时依赖）、CLAUDE.md（章程三模式 + 集成出口说明）
- **测试**：`tests/test_curator.py`、`tests/test_intel_api.py`（新建，httpx MockTransport，零新 dev 依赖）
- **依赖**：httpx（进主依赖；现仅 dev 组有）
- **部署前提**：feed-curator 同机 localhost（红线④不触碰——无鉴权面扩大）；数据前提：星级/摘要依赖 fix-analysis-cycle（feed-curator PR #21 + 用户填 key），未完成时情报流正常可用、星级显示为空
- **破坏性**：无
