# deputy · 项目开发约定

> 二号位 —— 一人公司的 AI 决策中枢。核心：**备料 → 门禁 → 释放**。
> 分身只能提议，用户批准后才落到真源。「人类做门禁」是不可动摇的设计。

## 开发流程（强制，两条铁律）

本项目的任何功能改动，**必须**同时遵守下面两条。不走这两步的改动一律不接受。

### 1. OpenSpec 驱动 —— 先立 spec，再写码

任何非平凡改动，按 OpenSpec 三段式走，不允许"聊着聊着就直接改代码"：

1. **propose** — 先写变更提案（改什么、为什么、影响哪些 spec），用 `/opsx:propose` 或 openspec-propose skill。
2. **等用户审阅通过** — proposal 是和用户达成一致的地方。未通过不动手。
3. **apply** — 通过后才实现，用 `/opsx:apply` 或 openspec-apply-change skill。
4. **archive** — 完成并验证后归档，用 `/opsx:archive` 或 openspec-archive-change skill。

> 为什么这么严：本项目的主人容易"上头想重做/搭平台/换技术栈"。OpenSpec 的 proposal
> 阶段就是刹车——强制"先想清楚要什么、写下来、达成一致"，再动手。这条纪律本身是产品的一部分。

例外：改错别字、格式、注释这类零风险改动，可直接改，不用走 OpenSpec。

### 2. TDD —— 先写测试，再写实现

遵循 Red → Green → Refactor：

1. **Red** — 先写测试，表达期望行为，运行确认它**失败**。
2. **Green** — 写最小实现让测试通过。
3. **Refactor** — 在测试保护下重构。

- 测试框架：pytest（见 `tests/`）。跑测试：`uv run pytest -q`。
- 每个 fixture 用独立临时 DB（见 `tests/conftest.py::fresh_db`），测试间不共享状态。
- 门禁是本项目的命门：**任何碰 propose/approve/reject 或真源写函数的改动，必须有对应测试**。
  尤其 `tests/test_mcp_contract.py` 那条"MCP 不得暴露直写工具"——它是「人类做门禁」的守门测试，不许删。
- 改完必须 `uv run pytest -q` 全绿才算完成。

## 架构速览

```
分身(龙虾/dodo, MCP client)          用户(看板/对话)
   │ 只能 propose(...)                │ 批准/驳回 + 直接操作
   ▼                                  ▼
app/mcp_server.py (FastMCP)      app/api.py (FastAPI)
   └──────────┬───────────────────────┘
              ▼
   app/store/  真源 + 门禁队列（业务规则在此强制）
              ▼
   SQLite (data/deputy.db)  ← gitignore，永不进仓库
```

- `app/domain.py` — 领域常量与规则（状态机、动作白名单）。业务真理的唯一来源。
- `app/store/projects.py` — 真源读写 + 规则（状态机、主攻唯一）。
- `app/store/proposals.py` — 门禁队列（propose→approve 派发→执行）。
- `app/mcp_server.py` — 分身接入。**故意不暴露任何直接写真源的工具。**
- `app/api.py` — 看板 Web API + 门禁审批端点。

## 红线（改任何东西都不许破）

1. **MCP 层绝不暴露直接写真源的工具** —— 分身的写操作只能走 `propose`。
2. **数据不出墙** —— `data/`、`*.db` 永远 gitignore；代码进仓库，数据留本地。
3. **业务规则只在 store 层强制** —— 状态机、主攻唯一等，不在 API/MCP 层重复实现。
4. **无鉴权仅限 localhost** —— 接网络/远程前必须先加鉴权。

## 常用命令

```bash
uv sync                                   # 装依赖
uv run python seed.py                     # 首次：从旧 projects.json 迁入
uv run uvicorn app.api:app --port 8899    # 看板 + 门禁 API
uv run python -m app.mcp_server           # MCP（供分身接入，stdio）
uv run pytest -q                          # 跑测试（改完必须全绿）
```
