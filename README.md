# deputy · 二号位

一人公司的 AI 决策中枢。核心一句话：**备料 → 门禁 → 释放**。

> 分身（龙虾/dodo/openclaw）只能**提议**，你**批准**后系统才改动真源。
> 人类做门禁，是这套系统唯一不可动摇的设计。

## 架构

```
分身（MCP 客户端：龙虾/dodo）           你（人类）
        │ 只能 propose(...)              │ 看板点击 / 审批提议
        ▼                                ▼
   FastMCP (app/mcp_server.py)      FastAPI (app/api.py)
        └──────────┬─────────────────────┘
                   ▼
         store/  真源 + 门禁队列
                   ▼
         SQLite (data/deputy.db)   ← .gitignore，永不进仓库
```

- **真源**：projects / todos / backlog / focus
- **门禁队列**：proposals（分身写这，你批准才落地）
- **业务规则**（状态机、主攻唯一）在 `app/domain.py` + `store/projects.py`，强制执行。

## 跑起来

```bash
uv sync                                  # 装依赖
uv run python seed.py                    # 从旧 projects.json 迁入现有项目（首次）
uv run uvicorn app.api:app --port 8899   # 看板 + 门禁 Web API
uv run python -m app.mcp_server          # MCP（供分身接入，stdio）
uv run pytest -q                         # 跑门禁逻辑测试
```

## 门禁流程（分身与你的分工）

1. 分身读 `get_state()` 备料，判断该改什么。
2. 分身 `propose(action, args, reason)` —— 扣进队列，**不生效**。
3. 你 `GET /api/proposals` 看待批，`POST /api/proposals/{id}/approve` 放行 or `/reject` 驳回。
4. 批准时系统派发到真源写函数，规则不过（如非法迁移）会拒，提议保持 pending。

分身可提议的动作见 `app/domain.py::PROPOSAL_ACTIONS`。

## 部署两处 · 数据不出墙

代码进私有 GitHub，两处 `git clone`；**数据靠 `.gitignore` 永远留本地**：

```
data/  *.db  →  已 gitignore
```

- 公司机器 clone 下来 = 纯净架构 + 公司自己的数据，副业记忆物理上不可能过去。
- 外面（Mac mini）clone 下来 = 同一架构 + 副业数据。
- 共享的只有"分身怎么工作"，不共享任何数据。

## 安全红线

- MCP/API **无鉴权**，仅限 localhost 自用，**绝不裸暴露公网**。
- 分身层（MCP）**故意不提供任何直接写真源的工具**——写只能走 propose。
