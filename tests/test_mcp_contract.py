"""MCP 契约：分身能读 + 提议 + 回填回答，但【没有】任何直接写真源/题目配置的工具。

这是"人类做门禁"在接口层的保证——若哪天有人给 MCP 加了直写工具，这个测试会红。
"""
from __future__ import annotations

import asyncio
import json


def _tool_names() -> set[str]:
    from app.mcp_server import mcp

    tools = asyncio.run(mcp.list_tools())
    return {t.name for t in tools}


def _call(name: str, args: dict) -> object:
    """以分身视角调 MCP 工具，解包返回值。

    SDK 返回形态不一：object 返回值 → list[TextContent(JSON)]；
    list 返回值 → (list[TextContent], {'result': [...]})。
    """
    from app.mcp_server import mcp

    result = asyncio.run(mcp.call_tool(name, args))
    if isinstance(result, tuple):
        return result[1]["result"]
    return json.loads(result[0].text)


def test_mcp_exposes_expected_tools():
    names = _tool_names()
    assert names == {
        "get_state", "get_project", "list_pending_proposals",
        "propose", "approve_proposal", "reject_proposal",
        "list_questions", "get_question", "submit_answer",
        "get_learning", "submit_lesson_note",
    }


def test_mcp_has_no_direct_write_tools():
    """真源/题目配置写函数名（add_todo/set_stage/add_question/...）绝不能作为 MCP 工具直接暴露。"""
    from app import domain

    names = _tool_names()
    forbidden = set(domain.PROPOSAL_ACTIONS)
    leaked = names & forbidden
    assert not leaked, f"MCP 泄漏了直写工具，绕过门禁：{leaked}"


def test_mcp_declares_avatar_instructions():
    """握手 instructions 携带精简章程：门禁铁律要点 + 指路总章程（见 add-avatar-guide）。

    注意：此通道是"白赚"——投递不依赖它（OpenClaw 未必透传），但既然声明了就必须有效。
    """
    from app.mcp_server import mcp

    instructions = mcp.instructions or ""
    assert instructions.strip(), "MCP 握手未声明 instructions（精简章程）"
    # 门禁铁律要点：提议门禁 + 绝不自批
    assert "propose" in instructions
    assert "approve" in instructions
    # 指路总章程：分身要知道唯一真源在哪
    assert "docs/avatar-guide.md" in instructions


def test_avatar_flow_list_then_submit(fresh_db):
    """分身视角端到端：取到期题 → 提交回答 → 回答可见且问题状态推进。"""
    from app.store import questions

    q = questions.add_question("测试题", "本周动向?", now="2026-07-23T00:00:00+00:00")

    # 1. 取到期题：新题从未运行 → first-run 到期，返回完整取料信息
    due = _call("list_questions", {})
    assert [item["id"] for item in due] == [q["id"]]
    assert due[0]["due_reason"] == "first-run"
    assert due[0]["prompt"] == "本周动向?" and due[0]["filter"] == {}

    # 2. 提交回答（run_date 显式给，保持测试确定性）
    answer = _call("submit_answer", {
        "question_id": q["id"],
        "body_md": "结论A [doc:1]",
        "sources": [{"doc_id": 1, "title": "t", "url": "https://example.com"}],
        "confidence": "high",
        "model": "龙虾",
        "run_date": "2026-07-23",
    })
    assert answer["version"] == 1 and answer["status"] == "new"

    # 3. 读题可见历史回答；题目状态推进后不再到期
    detail = _call("get_question", {"question_id": q["id"], "with_answers": 1})
    assert detail["last_run_at"] is not None
    assert detail["answers"][0]["body_md"] == "结论A [doc:1]"
    assert _call("list_questions", {}) == []  # 跑完即不再到期


def test_teaching_flow_get_then_submit(fresh_db):
    """分身教学端到端：取下一课 → 上完课存小结。"""
    from app.store import learning

    t = learning.add_track("具身智能", "能看懂前沿论文", now="2026-10-12T00:00:00+00:00")
    learning.set_curriculum(
        t["id"], [{"title": "A"}, {"title": "B"}], now="2026-10-12T00:00:00+00:00"
    )

    # 1. 备课：默认返回 active track，含进度与下一课
    tracks = _call("get_learning", {})
    assert [x["id"] for x in tracks] == [t["id"]]
    assert tracks[0]["next_point"]["title"] == "A"
    assert tracks[0]["progress"]["todo"] == 2

    # 2. 讲完课，小结直落
    note = _call("submit_lesson_note", {
        "track_id": t["id"], "point_title": "A",
        "body_md": "本课要点：…", "model": "龙虾",
    })
    assert note["point_title"] == "A"

    # 3. 详情可见小结；进度不变（自评是用户的事，分身不碰）
    detail = _call("get_learning", {"track_id": t["id"], "with_notes": 3})
    assert detail["notes"][0]["body_md"] == "本课要点：…"
    assert detail["next_point"]["title"] == "A"  # 仍是 A，等用户自评
