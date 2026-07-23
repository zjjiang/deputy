"""deputy（二号位）—— 一人公司的 AI 决策中枢。

核心：备料 → 门禁 → 释放。分身只能提议，用户批准后才落到真源。
- domain  领域常量与规则（状态机、动作白名单）
- store   持久层（SQLite）
- api     FastAPI（看板 Web API + 门禁）
- mcp     FastMCP（供龙虾/dodo 接入的工具）
"""
