# 预设问题 · 分身跑题 SOP

> 给谁看：龙虾（OpenClaw）。你通过 deputy MCP 的 `list_questions / get_question / submit_answer`
> 三个工具，定期基于 feed-curator 知识库回答用户预设的问题。
> deputy 不烧 token、不配 AI——脑子是你（龙虾侧配置的大模型），token 花在你读料和思考上。

## 0. 心跳与触发

OpenClaw cron（mini 上 `~/.openclaw/cron/jobs.json`，或经龙虾对话配置）建议每 30 分钟一次。
cron prompt 模板（照抄）：

```
检查 deputy 的预设问题：调用 list_questions 工具。
- 若返回空列表：什么都不用做，回复"无到期问题"即可。
- 若有到期题：对每一题，严格按 docs/thinking-sop.md 的流程处理
  （get_question 读历史 → 按 filter 从 feed-curator 取料 → 思考 → submit_answer 回填）。
- 不要跳过思考直接凑答案；材料不够就如实说明。
```

手动触发：用户在看板点「跑一次」→ 该题带 `manual-request` 标记 → 你下一次心跳取走。

## 1. 单题处理流程（两轮硬预算）

对每道到期题，**至多两轮取料，禁止更多**（成本可预算，行为可复现）：

```
① 读历史     get_question(question_id, with_answers=3)
             —— 上期答了什么、哪些线索在发酵。新回答必须是「增量」。
② 取料       按 filter 调 feed-curator（见 §2 映射表）
③ 初答       基于已有材料作答，自检：信息够不够？confidence + gaps 如实评
④ 条件补料   仅当 confidence != high 且 gaps 非空：按缺口调整检索再来一轮（最多这一次）
⑤ 定稿回填   submit_answer（引用、confidence、gaps、coverage 齐全）
```

## 2. 取料：filter → feed-curator API 映射

filter 字段是 feed-curator 侧语义，deputy 原样透传、不解释。映射：

| filter 字段 | feed-curator 参数 | 说明 |
|---|---|---|
| `kinds`（如 ["paper","article"]） | `GET /api/docs?kind=paper` | 每个值各查一次后合并 |
| `domain`（如 "具身智能"） | `domain_id=<feed-curator 的领域 id>` | 以 feed-curator `GET /api/domains` 实际 id 为准 |
| `days`（如 7） | 取回后按 `sort_time`/`published_at` 客户端过滤最近 N 天 | feed-curator 无时间参数 |
| `max_docs`（如 40） | `limit` | 取料上限，别超 |

正文：对入选条目 `GET /api/docs/{id}` 拿 `content_text` 全文。
**预算意识**：max_docs 条里挑与问题最相关的读（先看标题/摘要/星级），不必条条读全文。
feed-curator 服务没起/取料失败：如实提交一条说明失败原因的回答（confidence=low），**绝不编造**。

## 3. 回答规范

- **增量回答**：开头一两句「与上期相比的变化」；上期已答且无新进展的线索不再展开。
- **句级引用**：正文每个结论性句子挂 `[doc:<id>]`，只准引用 `sources` 里列出的条目。
- **sources**：`[{doc_id, title, url}, ...]`——正文引用的条目全都要在，一个不丢。
- **confidence**：high（信息充分）/ medium（有缺口但结论可用）/ low（材料答不了）。
- **meta**：`{gaps: ["缺 XX 维度近一周信息"], coverage: {items_scanned: 40, items_cited: 5}}`。
- **无料日降级**：确实没有相关更新时，正文写明「本期无重大相关更新」+ confidence=low。
  禁止硬凑、禁止把旧闻当新闻。
- **版本纪律**：`submit_answer` 同题同日每次提交生成新版本（v2、v3…），旧版自动标
  superseded。**只在确有新料/新结论时提交**——心跳里材料没变化就不要重复提交。

## 4. 题目进化（走门禁，不能自改）

你无权直接改/建问题。跑题跑出心得（时间窗太窄、该新盯一个角度）：

```
propose("edit_question", {question_id, prompt/cadence/filter...}, reason="...")
propose("add_question", {title, prompt, cadence, filter}, reason="...")
```

用户在门禁批准后才生效。回答的 meta.gaps 里写清「建议怎么调」能帮用户快速拍板。

## 5. mini 运维前置（一次性，人类操作）

1. feed-curator 服务在跑：`cd ~/Projects/feed-curator && start.sh`（127.0.0.1:9003）。
   不起来的话取料必失败，整个功能不可用。
2. （推荐）feed-curator 配 `DEEPSEEK_API_KEY` 并跑一轮 `/api/analyze/run`——给存量文档
   生成摘要/星级/领域，取料又准又省 token。不配也能跑，你直接读全文，token 稍重。
3. 确认 deputy 已按 `docs/lobster-setup.md` 挂进龙虾的 MCP（stdio，同机）。
4. 注册 §0 的 cron job。
