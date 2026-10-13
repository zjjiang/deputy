# add-avatar-guide 设计

## D1 · 为什么唯一真源放 deputy 仓库，而不是 OpenClaw 侧

OpenClaw 的 workspace 文件（AGENTS.md 等）虽是它每次会话必读的稳定通道，但内容在 mini 上、脱离 deputy 仓库——MCP 加工具、章程改规矩时没人记得同步，这就是 §5 人设烂掉的原因（只写 6 个工具、只覆盖作战处）。放仓库内：改工具面的 PR 被纪律强制同步章程（同一 PR、同一 review）。OpenClaw 侧只留一份"永不怎么变"的指路牌。

## D2 · 三投递通道与内容切分

| 通道 | 载体 | 放什么 | 不放什么 |
|---|---|---|---|
| ① 协议下发 | `FastMCP("deputy", instructions=…)` | 精简章程常量：身份一句 + 门禁铁律三条 + 指路章程 | 任何工具清单、映射表 |
| ② OpenClaw 系统提示 | lobster-setup §5（人肉贴一次） | 与①同构：身份 + 铁律 + 指路 | 同上——这是防漂移的关键 |
| ③ 工具 docstrings | mcp_server.py（现状保持） | 单工具纪律 + "详见 docs/…" | 全局地图（归章程） |

- **①② 内容同构**：都源自同一段铁律表述。①做成 `mcp_server.py` 模块级常量（不在 import 时读文件——构造期 IO 失败会连坐服务器启动；文本极小且稳定，常量最简）。章程文档是超集，开头嵌同一段铁律；两边语义同步靠 PR 纪律，不做自动 diff 校验（过度工程）。
- **②的可靠性依据**：cron 跑题链路已验证"OpenClaw 侧提示 + 指路仓库文档"模式可用（thinking-sop §0 → 读 SOP → 跑通）。①经逆向观察本机 OpenClaw 2026.2.26：嵌入式 agent 运行时无消费 server instructions 的实现、个别路径显式忽略 MCP servers——**大概率不透传**。故①定位为"白赚"（协议标准件、零成本，未来版本可能支持），②才是保底，投递不依赖①。
- **不新增 `get_guide()` 工具**（用户已拍板）：docstrings 指路 + §2 指路已够投递；若日后发现 instructions 不透传且 docstring 指路在实战中不被跟随，再议兜底工具。

## D3 · 章程文档结构（docs/avatar-guide.md）

1. **你是谁**——二号位一句定位 + deputy 是什么（纯逻辑后端，脑子在龙虾侧）
2. **三处地图**——作战处（get_state/get_project/propose）、军情处（list_questions/get_question/submit_answer + 取料走 feed-curator）、讲武堂（get_learning/submit_lesson_note），每处一句边界
3. **门禁铁律**——真源只读、写走 propose(reason 必填)、绝不自批 approve/reject（留给用户）、派生物直落例外（answers / lesson_notes）
4. **feed-curator 关系**——它是图书馆（订阅语料库，127.0.0.1:9003，MCP search_docs/get_doc 为主 REST 兜底）；三模式：奏折（心跳跑题，按 thinking-sop）、面圣（微信即答直检索，不进 deputy 不落档）、翻阅（看板内嵌，人的事）；边界三条：军情只吃语料不做全网检索、讲武堂素材次序自身知识→互联网→语料佐证、阅读状态/文档实体只存 curator（deputy 不落库）
5. **工具地图**——全部 11 个工具一表（读/门禁/派生物直落/留给用户 四类标注）——工具清单只活这一处
6. **SOP 索引**——跑题 → thinking-sop；上课 → teaching-sop
7. **运维前置**——feed-curator 要先起、cron 注册指路（吸收 thinking-sop §5 精神，不重复正文）

## D4 · lobster-setup.md 修正范围

- §5 重写为"铁律 + 指路"（删：工作方式细节、操作系统排序规则——后两者移进章程第 1/3 节）
- §4 顺手修："6 个工具"改为"工具集以章程工具地图为准"（验收对照指路，不再写死数量）

## D5 · 测试计划（TDD）

- **Red**：`tests/test_mcp_contract.py` 新增——`from app.mcp_server import mcp`，断言 `mcp.instructions` 非空且含关键词（propose / approve / avatar-guide 指路）；断言工具面不变（沿用既有工具名单断言，若有）。先跑确认失败。
- **Green**：mcp_server.py 加 `AVATAR_INSTRUCTIONS` 常量并传入 `FastMCP(instructions=…)`。
- **守门不动**："MCP 不得暴露直写工具"测试原样保留。
- 章程文档为纯 Markdown，不做内容解析测试（章节齐备靠 PR review 把关，spec 的 Scenario 即审阅清单）。
