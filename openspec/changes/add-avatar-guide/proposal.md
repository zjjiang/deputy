## Why

分身（龙虾/OpenClaw）的工作指引现在散落四处且已漂移：`docs/lobster-setup.md` §5 的"二号位人设"只覆盖作战处、还写着"6 个工具"（MCP 如今 11 个工具、三处齐备），靠人肉贴进 OpenClaw 系统提示必然过期；thinking-sop / teaching-sop 各管一段；工具 docstrings 只有单点纪律。最大空洞是 **feed-curator 与分身的关系对 agent 无文档**——面圣直连 9003、军情只吃订阅语料不做全网检索、讲武堂自身知识优先、阅读状态永远存 curator 不进 deputy，这些边界规则 agent 无处可查。指引需要唯一真源 + 不依赖人肉搬运的投递通道。

## What Changes

- **新增 `docs/avatar-guide.md`（分身总章程，唯一真源）**：身份与三处地图、门禁铁律（含 approve/reject 专属规则）、feed-curator 关系（奏折/面圣/翻阅三模式与取料边界）、SOP 索引（thinking-sop / teaching-sop）、运维前置。进仓库版本化，随代码走 PR。
- **`app/mcp_server.py`：`FastMCP` 构造加 `instructions=`** —— 精简版章程（身份 + 门禁铁律 + 指路 avatar-guide），握手时随协议下发。已验证本机 mcp 库支持该参数；OpenClaw 若透传则白赚一条常驻通道，不透传也无副作用。
- **`docs/lobster-setup.md` §5 人设段瘦身**：只留永不怎么变的铁律 + "细则读 deputy 仓库 docs/avatar-guide.md"指路，删掉会过期的工具清单与处室细则内联。
- **不新增/修改任何 MCP 工具、store、API 行为**——工具面零变化。

## Capabilities

### New Capabilities

- `avatar-guide`：分身指引的投递契约——章程文档的必含章节、MCP 握手下发精简章程（非空且含指路）、部署文档指路不内联细则。

### Modified Capabilities

（无——project-management / preset-questions / learning / intel-stream 四个现有能力的需求均不变。）

## Impact

- `app/mcp_server.py`：+1 构造参数，无行为面变化。
- `docs/avatar-guide.md`（新增）、`docs/lobster-setup.md`（§5 重写）。
- `tests/test_mcp_contract.py`：新增一条 instructions 契约测试；既有"MCP 不得暴露直写工具"守门测试原样保留。
- 不碰 store 层、API 层、数据库。
