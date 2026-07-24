# 龙虾（OpenClaw）接入 deputy 部署指南

把 deputy 作为 MCP 中枢挂到龙虾上，让分身能读你的项目全盘、并通过"提议"帮你干活。

> 前提认知：deputy **本身不烧 token、不需要配任何 AI API**。它是纯逻辑后端（存数据+门禁）。
> "智能"全来自龙虾里你配的大模型——token 花在龙虾侧，不在 deputy。

---

## 0. 适用场景

本指南针对 **龙虾与 deputy 在同一台机器**（如都在 Mac mini）的情况，用 **stdio** 方式接入——最简单、无网络、无鉴权烦恼。
若龙虾在另一台机器，需要改用 HTTP/SSE 传输并加鉴权，本指南不覆盖（届时另议）。

---

## 1. 拉代码 + 装依赖

```bash
git clone https://github.com/zjjiang/deputy.git
cd deputy
uv sync
```

## 2. 准备本地数据（数据不出墙）

代码从 GitHub 来，**数据只在本地**。首次初始化数据库：

```bash
# 方式一：从旧 projects.json 迁入（若这台机器上有）
uv run python seed.py /path/to/projects.json

# 方式二：全新空库（seed.py 找不到旧数据时自动建空库）
uv run python seed.py
```

数据库落在 `data/deputy.db`，已被 gitignore，**永远不会被推回仓库**。

> 两处部署各有各的 `data/deputy.db`：公司那台装公司的项目，Mac mini 装副业的。
> 共享的只有代码，绝不共享数据。

## 3. 验证 deputy 本身能跑

```bash
uv run pytest -q                          # 应全绿
uv run uvicorn app.api:app --port 8899    # 看板：浏览器开 http://127.0.0.1:8899
uv run python -m app.mcp_server           # MCP：能启动不报错即可（Ctrl-C 退出）
```

## 4. 在龙虾里配置 MCP（stdio）

在龙虾的 MCP 配置中加一个 server（不同龙虾版本配置文件位置/格式略有差异，键值照下面填）：

```json
{
  "mcpServers": {
    "deputy": {
      "command": "uv",
      "args": ["run", "python", "-m", "app.mcp_server"],
      "cwd": "/绝对路径/到/deputy"
    }
  }
}
```

- `cwd` 必须是 deputy 目录的**绝对路径**（龙虾要在这个目录下拉起进程，才能找到 `app/` 和 `data/`）。
- 若 `uv` 不在 PATH，把 `command` 换成 `uv` 的绝对路径（`which uv` 查）。

配好后重启龙虾，它应能看到 6 个工具：
`get_state` `get_project` `list_pending_proposals` `propose` `approve_proposal` `reject_proposal`。

## 5. 给龙虾装"二号位"人设（关键，A 档门禁的安全带）

deputy 的 MCP 在**结构上**保证分身不能直接写真源——但 `approve_proposal` 工具龙虾技术上也能调。
A 档（当前采用）靠**龙虾的系统提示**守住"分身不自己批"。把下面这段写进龙虾的角色/系统提示：

```
你是"二号位"——用户一人公司的 AI 决策副手。你的职责是备料和提议，不是替他决策。

铁律（不可违反）：
1. 任何要改动 deputy 真源的操作，只能用 propose(action, args, reason) 提交，
   扣进门禁队列等用户拍板。绝不替用户做决定。
2. 【绝不主动调用 approve_proposal / reject_proposal】——批准和驳回是用户的专属动作。
   只有当用户明确说"批准/ok/通过第N条"时，你才代为调用 approve_proposal(N)；
   用户说"驳回/不行第N条"时才调 reject_proposal。没有明确指令，一律不碰这两个工具。
3. propose 时 reason 必须写清"为什么提这个、关联哪个项目"，方便用户一眼拍板。

工作方式：
- 先 get_state 读全盘（项目/状态/todo/需求池/此刻聚焦）再判断，不凭空臆测。
- 你只排优先级、备料、提议；执行细节和最终决策留给用户。
- 该沉默时沉默：没有真正值得报的事，就不打扰。

用户的操作系统（排序时遵循）：
- 稀缺的是他的时间/精力，不是钱。周末=唯一深度窗口，工作日只挂机维护。
- 项目分桶：主攻(同时仅1个)/收租(维护)/半活跃(伙伴主导)/雪藏(等扳机)。
- 合伙人分担是核心打法；雪藏项目的扳机是否触发，只有用户能判断。
```

> 这段人设 = A 档门禁的安全带。缺了它，龙虾可能自己 propose 完自己 approve，门禁形同虚设。

## 6. 跑通第一条链路（验收）

在龙虾对话里：

1. 你说："看看我的项目全盘。" → 龙虾调 `get_state`，复述现状。
2. 你说："③已经不是主攻了，帮我处理下。" → 龙虾 `propose(set_stage, {project_id, stage:frozen}, reason=...)`。
3. 龙虾告诉你"提议 #N 已入队，等你拍板"。**它此时不应自己批。**
4. 你去看板（8899）看到待批提议，或在对话里说"批准第N条"。
5. 批准后真源改变，看板刷新可见。

跑通这一遍，"分身提议 → 你拍板 → 落库"的中枢就活了。

---

## 安全红线（勿破）

- **无鉴权，仅限 localhost。** 同机 stdio 无暴露风险；一旦要跨机/远程，必须先加鉴权，否则中枢裸奔。
- **数据不出墙。** `data/`、`*.db` 永远 gitignore。公司那台的项目数据绝不推仓库、绝不进个人环境。
- **微信入口是后话。** 现阶段门禁发生在龙虾对话里；接微信（WorkBuddy 等）是路线图阶段4，届时务必连同鉴权一起做。
