"""MCP 契约：分身能读+提议，但【没有】任何直接写真源的工具。

这是"人类做门禁"在接口层的保证——若哪天有人给 MCP 加了直写工具，这个测试会红。
"""
from __future__ import annotations

import asyncio


def _tool_names() -> set[str]:
    from app.mcp_server import mcp

    tools = asyncio.run(mcp.list_tools())
    return {t.name for t in tools}


def test_mcp_exposes_expected_tools():
    names = _tool_names()
    assert names == {
        "get_state", "get_project", "list_pending_proposals",
        "propose", "approve_proposal", "reject_proposal",
    }


def test_mcp_has_no_direct_write_tools():
    """真源写函数名（add_todo/set_stage/...）绝不能作为 MCP 工具直接暴露。"""
    from app import domain

    names = _tool_names()
    forbidden = set(domain.PROPOSAL_ACTIONS)  # add_todo, set_stage, set_focus...
    leaked = names & forbidden
    assert not leaked, f"MCP 泄漏了直写工具，绕过门禁：{leaked}"
