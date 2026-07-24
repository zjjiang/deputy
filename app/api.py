"""FastAPI —— 看板 Web API + 门禁审批端点。

给你（人类）用的接口：
  - 直接操作真源（你在看板上点，属于"你自己拍板"，不走提议队列）
  - 审批分身的提议（approve/reject）

分身不走这里，走 MCP（app/mcp_server.py）。
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import domain
from .store import db, projects, proposals

WEB_DIR = Path(__file__).resolve().parent / "web"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _guard(fn):
    """把领域错误映射成 400，找不到映射成 404。"""
    try:
        return fn()
    except domain.DomainError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e).strip('"')) from e


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="deputy 决策中枢", version="0.1.0", lifespan=lifespan)


# ---------- 读 ----------

@app.get("/api/state")
def get_state() -> dict[str, Any]:
    return projects.get_state()


@app.get("/api/project/{project_id}")
def get_project(project_id: str) -> dict[str, Any]:
    return _guard(lambda: projects.get_project(project_id))


# ---------- 门禁：你审批分身的提议 ----------

@app.get("/api/proposals")
def list_proposals(status: str | None = "pending") -> list[dict[str, Any]]:
    # 空字符串（?status=）视为"全部"，与前端"含历史"请求一致。
    return proposals.list_proposals(status or None)


class DecideBody(BaseModel):
    note: str = ""


@app.post("/api/proposals/{proposal_id}/approve")
def approve(proposal_id: int) -> dict[str, Any]:
    return _guard(lambda: proposals.approve(proposal_id, _now()))


@app.post("/api/proposals/{proposal_id}/reject")
def reject(proposal_id: int, body: DecideBody) -> dict[str, Any]:
    return _guard(lambda: proposals.reject(proposal_id, _now(), body.note))


@app.post("/api/proposals/clear")
def clear_decided() -> dict[str, Any]:
    return proposals.clear_decided()


# ---------- 你直接操作真源（看板上你自己点，不走提议）----------

class TodoAdd(BaseModel):
    project_id: str
    text: str


class TodoToggle(BaseModel):
    project_id: str
    todo_id: str
    done: bool = True


class TodoEdit(BaseModel):
    project_id: str
    todo_id: str
    text: str


class TodoRemove(BaseModel):
    project_id: str
    todo_id: str


class FocusBody(BaseModel):
    summary: str
    items: list[str] = []
    by: str = "我"


class ProjectAdd(BaseModel):
    name: str
    stage: str = "spark"
    drive: str = "self"
    kind: str = "biz"


class ProjectRename(BaseModel):
    project_id: str
    name: str


class ProjectStage(BaseModel):
    project_id: str
    stage: str


class ProjectKind(BaseModel):
    project_id: str
    kind: str


class ProjectTrigger(BaseModel):
    project_id: str
    trigger: str


class BacklogAdd(BaseModel):
    text: str


@app.post("/api/todo/add")
def todo_add(b: TodoAdd) -> dict[str, Any]:
    return _guard(lambda: projects.add_todo(b.project_id, b.text))


@app.post("/api/todo/toggle")
def todo_toggle(b: TodoToggle) -> dict[str, Any]:
    return _guard(lambda: projects.toggle_todo(b.project_id, b.todo_id, b.done))


@app.post("/api/todo/edit")
def todo_edit(b: TodoEdit) -> dict[str, Any]:
    return _guard(lambda: projects.edit_todo(b.project_id, b.todo_id, b.text))


@app.post("/api/todo/remove")
def todo_remove(b: TodoRemove) -> dict[str, Any]:
    return _guard(lambda: projects.remove_todo(b.project_id, b.todo_id))


@app.post("/api/focus")
def set_focus(b: FocusBody) -> dict[str, Any]:
    return _guard(lambda: projects.set_focus(b.summary, b.items, b.by))


@app.post("/api/project/add")
def project_add(b: ProjectAdd) -> dict[str, Any]:
    return _guard(lambda: projects.add_project(b.name, b.stage, b.drive, b.kind))


@app.post("/api/project/rename")
def project_rename(b: ProjectRename) -> dict[str, Any]:
    return _guard(lambda: projects.rename_project(b.project_id, b.name))


@app.post("/api/project/stage")
def project_stage(b: ProjectStage) -> dict[str, Any]:
    return _guard(lambda: projects.set_stage(b.project_id, b.stage))


@app.post("/api/project/kind")
def project_kind(b: ProjectKind) -> dict[str, Any]:
    return _guard(lambda: projects.set_kind(b.project_id, b.kind))


@app.post("/api/project/trigger")
def project_trigger(b: ProjectTrigger) -> dict[str, Any]:
    return _guard(lambda: projects.set_trigger(b.project_id, b.trigger))


@app.post("/api/project/{project_id}/archive")
def project_archive(project_id: str) -> dict[str, Any]:
    return _guard(lambda: projects.archive(project_id))


@app.post("/api/project/{project_id}/delete")
def project_delete(project_id: str) -> dict[str, Any]:
    return _guard(lambda: projects.delete_project(project_id))


@app.post("/api/backlog/add")
def backlog_add(b: BacklogAdd) -> dict[str, Any]:
    return _guard(lambda: projects.add_to_backlog(b.text))


# ---------- 静态看板 ----------

@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
