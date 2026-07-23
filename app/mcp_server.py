"""FastMCP —— 供分身（龙虾/dodo/openclaw）接入的工具层。

门禁铁律（A 档）：分身能【读】全部，但任何【写】都只能走 propose(...)，
落进门禁队列等用户批准。这里【故意】不暴露任何直接写真源的工具。
用户的批准/驳回走 Web API 或 approve_proposal（留给"你"在对话里用）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import domain
from .store import db, projects, proposals

mcp = FastMCP("deputy")

db.init_db()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
      - set_trigger     {project_id, trigger}
      - add_project     {name, stage?, drive?, kind?}
      - rename_project  {project_id, name}
      - add_to_backlog  {text}                 丢想法进需求池

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
