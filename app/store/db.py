"""SQLite 连接与 schema —— 决策中枢的持久层。

设计要点：
  - 真源表：projects / todos / backlog / meta(单行 focus)
  - 门禁表：proposals（分身只能写这，用户批准后才落到真源）
  - WAL 模式 + 外键，单文件、零运维。
"""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "deputy.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id       TEXT PRIMARY KEY,
    name     TEXT NOT NULL,
    stage    TEXT NOT NULL,
    drive    TEXT NOT NULL,
    kind     TEXT NOT NULL,
    trigger  TEXT NOT NULL DEFAULT '',
    ord      INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS todos (
    id          TEXT NOT NULL,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    text        TEXT NOT NULL,
    done        INTEGER NOT NULL DEFAULT 0,
    ord         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (project_id, id)
);

CREATE TABLE IF NOT EXISTS backlog (
    id      TEXT PRIMARY KEY,
    text    TEXT NOT NULL,
    status  TEXT NOT NULL DEFAULT '待归类',
    ord     INTEGER NOT NULL DEFAULT 0
);

-- 单行表：此刻聚焦。id 恒为 1。
CREATE TABLE IF NOT EXISTS focus (
    id       INTEGER PRIMARY KEY CHECK (id = 1),
    summary  TEXT NOT NULL DEFAULT '',
    items    TEXT NOT NULL DEFAULT '[]',   -- JSON 数组
    by_who   TEXT NOT NULL DEFAULT '自动'
);

-- 门禁队列：分身的提议扣在这里，等用户批准/驳回。
CREATE TABLE IF NOT EXISTS proposals (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    action   TEXT NOT NULL,               -- domain.PROPOSAL_ACTIONS 之一
    args     TEXT NOT NULL,               -- JSON
    reason   TEXT NOT NULL DEFAULT '',    -- 分身为什么提这个
    by_who   TEXT NOT NULL DEFAULT '分身',
    status   TEXT NOT NULL DEFAULT 'pending',  -- pending/approved/rejected
    created  TEXT NOT NULL,               -- ISO 时间（由调用方传入）
    decided  TEXT,                        -- 批准/驳回时间
    note     TEXT NOT NULL DEFAULT ''     -- 用户驳回理由或备注
);
CREATE INDEX IF NOT EXISTS idx_proposals_status ON proposals(status);

-- 预设问题：用户配置「要 AI 持续关注什么」，分身经 MCP 取到期题、回填回答。
-- 注意：answers 不走门禁（派生物非真源），但 questions 的建/改走门禁白名单。
CREATE TABLE IF NOT EXISTS questions (
    id            TEXT PRIMARY KEY,            -- q1/q2/... 递增
    title         TEXT NOT NULL,
    prompt        TEXT NOT NULL,               -- 给 AI 的完整问题文本
    filter_json   TEXT NOT NULL DEFAULT '{}',  -- {kinds?, domain?, days?, max_docs?}
    cadence       TEXT NOT NULL DEFAULT 'daily',  -- daily/weekly/manual
    active        INTEGER NOT NULL DEFAULT 1,
    requested_at  TEXT,                        -- 手动「跑一次」UTC 标记，submit 时清空
    last_run_at   TEXT,                        -- 最近成功回答时间（UTC）
    ord           INTEGER NOT NULL DEFAULT 0,
    created       TEXT NOT NULL                -- UTC ISO，调用方传入
);

-- 回答档案：append-only 版本化。同题同日每次提交 = 新版本，
-- 旧版本标 superseded 保留可查，最新版为当前结论。
CREATE TABLE IF NOT EXISTS answers (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id  TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    body_md      TEXT NOT NULL,
    sources      TEXT NOT NULL DEFAULT '[]',  -- JSON: [{doc_id,title,url}...]
    confidence   TEXT NOT NULL DEFAULT '',    -- high/medium/low
    meta_json    TEXT NOT NULL DEFAULT '{}',  -- {gaps?, coverage?}
    model        TEXT NOT NULL DEFAULT '',    -- 哪个分身跑的（龙虾/dodo）
    run_date     TEXT NOT NULL,               -- YYYY-MM-DD，东八区日历日，边界层传入
    version      INTEGER NOT NULL DEFAULT 1,  -- 同题同日递增
    status       TEXT NOT NULL DEFAULT 'new', -- new/read/superseded
    read_at      TEXT,                        -- 标已读时间（UTC），对标 todos.done_at
    created      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_answers_q ON answers(question_id, run_date, version);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, isolation_level=None)  # autocommit; 我们显式管理事务
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.executescript(SCHEMA)
        # 幂等迁移：给 todos 加 done_at（历史数据留 NULL）
        cols = [r[1] for r in conn.execute("PRAGMA table_info(todos)").fetchall()]
        if "done_at" not in cols:
            conn.execute("ALTER TABLE todos ADD COLUMN done_at TEXT")


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    """每次操作一个连接；写操作用 BEGIN IMMEDIATE 串行化，避免并发写打架。"""
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """写事务：BEGIN IMMEDIATE 拿写锁，异常回滚。"""
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()
