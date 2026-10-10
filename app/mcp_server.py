"""FastMCP —— 供分身（龙虾/dodo/openclaw）接入的工具层。

门禁铁律（A 档）：分身能【读】全部，但触及真源（projects/todos/backlog/focus）
和题目配置（questions）的【写】只能走 propose(...)，落进门禁队列等用户批准。
这里【故意】不暴露任何直接写真源的工具。唯一的例外是 submit_answer：
回答（answers）是用户预设之问的派生物，非真源，走专属工具直接落库（见 spec）。
用户的批准/驳回走 Web API 或 approve_proposal（留给"你"在对话里用）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from mcp.server.fastmcp import FastMCP

from . import domain
from .store import db, projects, proposals, questions

mcp = FastMCP("deputy")

db.init_db()

_TZ_CN = ZoneInfo("Asia/Shanghai")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_cn() -> str:
    """run_date 口径：东八区日历日（见 change design D2）。"""
    return datetime.now(_TZ_CN).strftime("%Y-%m-%d")


# ============ 读：分身随时可读，无需批准（可逆、安全）============

@mcp.tool()
def get_state() -> dict:
    """读全盘：所有项目及其 stage(生命周期)/drive(谁在推)/kind(类型)/todos/扳机，
    + 需求池 + 此刻聚焦 + 各维度中文含义。这是分身"备料"的起点。"""
    return projects.get_state()


@mcp.tool()
def get_project(project_id: str) -> dict:
    """读单个项目完整详情。project_id 如 p1/p3/opc 等。"""
    return projects.get_project(project_id)


@mcp.tool()
def list_pending_proposals() -> list[dict]:
    """看当前还挂着、等用户批的提议队列（分身自查，避免重复提同一件事）。"""
    return proposals.list_proposals("pending")


# ============ 预设问题：读到期题 + 回填回答（answers 为派生物，不经门禁）============

@mcp.tool()
def list_questions(all: bool = False) -> list[dict]:
    """【预设问题】取要跑的问题。默认只回【到期题】（日常唯一入口）；
    all=True 返回全部（调试用）。每条含 prompt/filter/cadence/due/due_reason。

    due_reason: first-run(从未跑过) / scheduled(超过周期) / manual-request(用户点过"跑一次")。
    有到期题就按 docs/thinking-sop.md 处理：按 filter 从 feed-curator 取料 →
    思考（增量：先 get_question 读历史）→ submit_answer 回填。
    """
    return questions.list_questions(_now(), due_only=not all)


@mcp.tool()
def get_question(question_id: str, with_answers: int = 3) -> dict:
    """【预设问题】读单题详情 + 最近 N 天的每日最新版回答（默认 3 天）。

    提交前先读历史：新回答写「与上期相比的变化」，不要重复上期内容（增量回答）。
    """
    return questions.get_question(question_id, with_answers=max(0, with_answers))


@mcp.tool()
def submit_answer(
    question_id: str,
    body_md: str,
    sources: list[dict[str, Any]] | None = None,
    confidence: str = "",
    model: str = "",
    meta: dict[str, Any] | None = None,
    run_date: str | None = None,
) -> dict:
    """【预设问题】回填回答：直接落库（回答是派生物非真源，不走门禁）。
    同题同日每次提交生成新版本（v1/v2/...），旧版本标 superseded 保留可查。

    提交纪律（详见 docs/thinking-sop.md）：
      - 只在确有新料/新结论时提交；无重大更新就写明"本期无重大相关更新" + confidence=low
      - body_md 里句级挂引用，只准引用 sources 里给到的条目，禁止编造
      - sources: [{doc_id, title, url}...]；meta: {gaps:[...], coverage:{items_scanned, items_cited}}
      - confidence: high/medium/low；model: 你的名字（如 龙虾/dodo）
      - run_date 缺省按东八区今天算
    """
    return questions.submit_answer(
        question_id,
        body_md,
        sources=sources,
        confidence=confidence,
        model=model,
        run_date=run_date or _today_cn(),
        now=_now(),
        meta=meta,
    )


# ============ 写：一律走提议门禁。分身不能直接改真源 ============

@mcp.tool()
def propose(action: str, args: dict, reason: str) -> dict:
    """【门禁】分身提交一条写操作提议，扣进队列等用户批准，绝不直接生效。

    action 取值（及 args 必填键）：
      - set_focus       {summary, items?}      更新"此刻聚焦"
      - add_todo        {project_id, text}     给项目加 todo
      - toggle_todo     {project_id, todo_id, done?}
      - edit_todo       {project_id, todo_id, text}
      - remove_todo     {project_id, todo_id}
      - set_stage       {project_id, stage}    受状态机+主攻唯一约束
      - set_drive       {project_id, drive}
      - set_kind        {project_id, kind}     biz(商业)/tool(自用工具)
      - set_trigger     {project_id, trigger}
      - add_project     {name, stage?, drive?, kind?}
      - rename_project  {project_id, name}
      - add_to_backlog  {text}                 丢想法进需求池
      - reorder_project {project_id, target_id, position}  排序：把 project_id 插到
                                                target_id 前(before)/后(after)

    reason 必填：一句话说清"为什么提这个、关联哪个项目/判断"，供用户在门禁处快速拍板。
    """
    return proposals.propose(action, args, reason, _now(), by="分身")


@mcp.tool()
def approve_proposal(proposal_id: int) -> dict:
    """【门禁·放行】用户批准某条提议，系统才真正执行它（派发到真源写函数）。
    这一步代表"人拍了板"。分身不应自己调用这个——它是留给用户在对话里说"批准X"时用的。"""
    return proposals.approve(proposal_id, _now())


@mcp.tool()
def reject_proposal(proposal_id: int, note: str = "") -> dict:
    """【门禁·驳回】用户驳回某条提议，不执行。note 可附理由。同样是留给用户的动作。"""
    return proposals.reject(proposal_id, _now(), note)


if __name__ == "__main__":
    mcp.run()
