## Context

军情处现有奏折面（preset-questions 能力）。feed-curator 侧 `GET /api/docs` 响应已含 stars/summary/domains/is_read/is_favorite 与 total 分页；`POST /api/docs/{doc_id}/reading` 可写回；`GET /api/domains` 提供领域列表。deputy 至今零 HTTP 客户端（httpx 仅在 dev 组）。用户确认内嵌方案（B）。数据前提：星级内容依赖 feed-curator 判定循环（fix-analysis-cycle，PR #21 + 用户填 key），未完成不阻塞本能力。

## Goals / Non-Goals

**Goals**
- 军情 tab 双区：奏折（不动）+ 情报流（领域/类型/四星筛选、排序、分页、已读收藏）
- 集成收敛在唯一出口模块；降级可控；状态存储零迁移

**Non-Goals**
- 不做 deputy 侧文档缓存/索引/副本（每次实时转发，feed-curator 本地毫秒级）
- 不做 feed-curator 写路径之外的内容管理（订阅管理留在 feed-curator 自己的 UI/admin）
- 分身 MCP 面零变更（分身取情报走 feed-curator 自己的 MCP：search_docs/recommend_articles）
- 不做全文阅读器（点标题开原文 url；get_doc 深读是分身的事）

## Decisions

**D1 集成唯一出口：`app/services/curator.py` + httpx 进主依赖**
全仓对 feed-curator 的 HTTP 访问只此一处：`curator.list_docs(...)/domains()/set_reading(...)`，base URL `CURATOR_BASE_URL`（默认 `http://127.0.0.1:9003`，env 可配）、`timeout=2.0`、非 200/超时/连接错误统一抛 `CuratorUnavailable`（新异常，映射 503）。备选「前端直连 9003」被否：跨源（8899→9003）要 CORS、把图书馆端口暴露给浏览器、降级失控——后端代理是唯一入口。

**D2 状态归属不破：代理不落库**
已读/收藏 = deputy 转发 feed-curator 写 API，deputy 无任何相关表；奏折已阅（answers.status）与课程掌握（point.status）语义不受影响。章程「状态跟着实体走」原文照旧成立，仅军情处模式描述从两模式扩为三模式。

**D3 代理端点三只：`/api/intel/docs`、`/api/intel/domains`、`/api/intel/reading/{doc_id}`**
`GET /api/intel/docs?domain_id&kind&min_stars&sort&page`（page→offset 换算，每页 30）；`GET /api/intel/domains`（筛选下拉数据）；`POST /api/intel/reading/{doc_id}`（body: is_read/is_favorite，转发 reading API）。响应原样透传 feed-curator JSON（deputy 不再加工——字段已在对面装饰好）。502/503：CuratorUnavailable → 503 带降级文案。

**D4 feed-curator 侧配套：`add-docs-star-sort`（其仓库独立 change）**
`GET /api/docs` 增 `sort=time|stars`（复用网页版 `_latest_ok_analysis_ids` 的现成 join）与 `min_stars`（1-5 门槛）。**未合入时情报流不阻塞**：curator 客户端传参前探测——若 422/忽略未知参数则前端隐藏「仅四星」「按星级」控件，退化时间序。探测方式：首次请求带 `sort=stars`，失败标记会话级降级。

**D5 降级语义：闭馆 ≠ 断电**
`CuratorUnavailable` 仅影响情报流分区；奏折（questions store）与 deputy 全部其他功能零感知。前端降级卡带「重试」按钮（重新 fetch 即可）。

**D6 前端：军情 tab 双区自持**
奏折区（现 renderQuestions 改挂「奏折」分区标识，逻辑不动）+ 情报流区（筛选条 + 卡片列表 + 分页；筛选/页码存 `window._intel`，不进 5s 轮询——**情报流不参与自动刷新**，手动重试/翻页才拉，避免轮询打图书馆）。条目操作：已读/收藏 → 代理写回 → 按返回刷新单条。样式复用 `.kind-badge`/`.srcs`/`.ans` 族。

**D7 测试：httpx MockTransport，零新 dev 依赖**
curator 客户端用 `httpx.MockTransport` 注入假 feed-curator（正常/超时/非 200 三态）；API 测试走 monkeypatch curator 模块函数。前端无自动化（沿用 smoke 目检）。

**D8 章程更新随本 change**：CLAUDE.md 军情处条目改三模式（奏折/面圣/翻阅）+ 集成出口约定（「全部 HTTP 访问只经 curator 模块」写进章程，防将来第二处散落调用）。

## Risks / Trade-offs

- [feed-curator API 形状变化打崩代理] → 唯一出口 + 结构化错误 + 降级提示；两边各有 OpenSpec，接口演进会在对方 change 的 Impact 里声明
- [每次实时转发，无缓存] → 本机调用毫秒级、分页 30 条，无性能压力；缓存引入一致性负担，不值
- [四星门槛依赖判定数据] → 未判定条目 stars 为空自然被 min_stars 过滤掉（feed-curator 侧 `stars >= min_stars` 语义），属预期行为；降级路径见 spec「未判定条目」
- [sort/min_stars 参数未合入窗口期的 UI 抖动] → D4 的探测降级，控件隐藏而非报错

## Migration Plan

纯新增 + 前端分区改造。回滚 = revert（curator.py/端点/前端分区均可独立移除，无数据残留）。

## Open Questions

无——集成方式（内嵌 B）、双区形态、状态归属边界均已在探索阶段与用户对齐。
