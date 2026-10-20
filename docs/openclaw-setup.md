# OpenClaw（龙虾）装机指南 —— 参谋部全链路接入

> 分工：本文管**从一台空 Mac mini 到龙虾能干活**——装 OpenClaw 本体、接渠道、挂
> deputy + feed-curator 双 MCP、装人设、注册心跳、验收。
> deputy 本体自身的装法（clone/uv sync/seed/pytest）见 `docs/lobster-setup.md` §1–3；
> 分身行为规范见 `docs/avatar-guide.md`。

## 0. 拓扑：一台 mini 上跑四样

| 组件 | 角色 | 形态 |
|---|---|---|
| OpenClaw gateway | 渠道接入 + 会话 + 调度（cron/心跳） | LaunchAgent 常驻；脑子=你配的大模型，token 花在这 |
| deputy | 参谋部：看板 8899 + 门禁 + 真源 | 按需拉起（MCP stdio）；看板想常开自己起 uvicorn |
| feed-curator | 图书馆：订阅语料 + 阅读状态 | `start.sh` 常驻 127.0.0.1:9003（MCP + REST） |
| SQLite ×2 | deputy / feed-curator 各自的库 | `data/` 各自本地，**数据不出墙** |

## 1. 装 OpenClaw 本体

```bash
npm install -g openclaw@latest   # 或官方一键脚本，见 docs.openclaw.ai/install（需 Node 24.16+/26+）
openclaw doctor                  # 体检：环境/依赖/配置
openclaw onboard --install-daemon  # 向导：gateway + 工作区 + 模型 key，并注册 LaunchAgent 常驻
openclaw health                  # 确认 gateway 活着
```

- 代理环境（Clash）：安装/升级前 `export https_proxy=http://127.0.0.1:7897`。
- 模型 key 在 onboard/configure 里配——**智能全在龙虾侧**，deputy 和 feed-curator 都不烧 token。
- **老版本必须先升级**：`openclaw update`。MCP 子命令与 `mcp.servers` 配置是 2026.10 版的形态。

## 2. 起两个本地服务

1. **deputy**：照 `lobster-setup.md` §1–3（clone → `uv sync` → seed → `uv run pytest -q` 全绿）。
   MCP 走 stdio，龙虾会话时自动拉起，无需常驻；看板常开：
   `uv run uvicorn app.api:app --port 8899`（建议 launchd 托管）。
2. **feed-curator**：`cd ~/Projects/feed-curator && start.sh`（9003）。
   **它没起 = 军情处取料必失败**，龙虾会如实报 confidence=low。
   （推荐）配 `DEEPSEEK_API_KEY` 跑一轮 `/api/analyze/run`，取料又准又省 token。

## 3. 挂双 MCP（核心步骤）

用 `openclaw mcp` 命令，配置落 `~/.openclaw/openclaw.json` 顶层 `mcp.servers`：

```bash
# deputy（stdio，同机；路径必须绝对，uv 不在 gateway 的 PATH 就用 which uv 的绝对路径）
openclaw mcp add deputy --command uv --arg run --arg python --arg -m --arg app.mcp_server \
  --cwd /Users/<你>/Projects/deputy

# feed-curator（streamable-http）
openclaw mcp add curator --url http://127.0.0.1:9003/mcp --transport streamable-http

# 体检：两条都要能列出工具
openclaw mcp doctor deputy --probe
openclaw mcp doctor curator --probe
openclaw mcp status --verbose
```

等价的 config 形状（手编 `openclaw.json`）：

```json5
{ "mcp": { "servers": {
    "deputy":  { "command": "uv", "args": ["run", "python", "-m", "app.mcp_server"],
                 "cwd": "/Users/<你>/Projects/deputy", "transport": "stdio", "enabled": true },
    "curator": { "url": "http://127.0.0.1:9003/mcp", "transport": "streamable-http", "enabled": true }
} } }
```

> 改 config 后 gateway 需要 reload/重启，工具才会刷新。
> 连通后的工具面对照总章程 `docs/avatar-guide.md` §5：deputy 11 个 +
> curator 的 `search_docs` / `get_doc`。

## 4. 装人设（A 档门禁的安全带）

工作区在 `~/.openclaw/workspace/`。把 `lobster-setup.md` §5 的"二号位"铁律段写进
`AGENTS.md`（每次会话必读），并写明"开工先读 deputy 仓库 `docs/avatar-guide.md`"。

**纪律：人设里只有身份 + 铁律 + 指路**。工具清单、取料映射等易变细则一律不进人设——
指路章程，永不过期。

## 5. 注册心跳（军情处奏折）

```bash
openclaw cron add   # 参数见 openclaw cron add --help；约每 30 分钟一次
```

prompt 照抄 `docs/thinking-sop.md` §0 的模板。验证：`openclaw cron list` →
`openclaw cron run <name>`（debug 跑一轮）→ `openclaw cron runs` 看历史。
（也可以直接跟龙虾说"帮我注册每 30 分钟的心跳，prompt 如下：…"。）

## 6. 接渠道

`openclaw channels add`（Telegram / WhatsApp / 微信等——微信属区域平台渠道，官方有
WeChat 渠道文档，按需接）。没接渠道也能用：`openclaw tui` 或 Control UI（`openclaw dashboard`）。

## 7. 验收三条链路

1. **作战（门禁）**："看看我的项目全盘" → 它调 `get_state` 复述；
   "把 X 移出主攻" → `propose` 入队，**它不自己批**；你说"批准第 N 条" → 生效，看板可见。
2. **军情（奏折）**：等心跳或看板点"跑一次" → 它取料思考 → `submit_answer` →
   军报区出稿（句级引用 + confidence 齐全）。
3. **讲武堂**："开课" → `get_learning` 取下一课讲解 → 你说"懂了" → 门禁代写状态 +
   `submit_lesson_note` 小结落库，讲武堂 tab 可见。

## 安全红线

- **无鉴权仅限 localhost**：gateway、8899 看板、9003 图书馆都别暴露公网；远程访问先加鉴权。
- **数据不出墙**：`data/*.db`、`~/.openclaw/`（记忆/凭据）全留本机，永不进仓库、不推云端。
