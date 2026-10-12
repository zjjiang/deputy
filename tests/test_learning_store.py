"""learning store 行为：track CRUD、大纲门禁语义（同名继承）、自评状态机、课程小结、下一课判定。"""
from __future__ import annotations

import pytest

T0 = "2026-10-12T00:00:00+00:00"


def _mk_track(fresh_db, title="具身智能", goal="能看懂前沿论文", **kw):
    from app.store import learning

    kw.setdefault("now", T0)
    return learning.add_track(title, goal, **kw)


def _curriculum(fresh_db, track_id, titles, **kw):
    """按标题列表落一份大纲（summary 留空）。"""
    from app.store import learning

    kw.setdefault("now", T0)
    return learning.set_curriculum(track_id, [{"title": t} for t in titles], **kw)


def _points(fresh_db, track_id):
    from app.store import learning

    return {p["title"]: p for p in learning.get_track(track_id)["points"]}


# ---------- track CRUD ----------

def test_add_track_ids_and_defaults(fresh_db):
    t1 = _mk_track(fresh_db)
    t2 = _mk_track(fresh_db, title="自动驾驶", goal="g2")
    assert t1["id"] == "l1" and t2["id"] == "l2"
    assert t1["status"] == "active" and t2["ord"] == t1["ord"] + 1
    assert t1["progress"] == {"total": 0, "learned": 0, "todo": 0, "revisit": 0}


def test_add_track_empty_title_or_goal_rejected(fresh_db):
    with pytest.raises(Exception):
        _mk_track(fresh_db, title="  ")
    with pytest.raises(Exception):
        _mk_track(fresh_db, goal="")


def test_edit_track(fresh_db):
    from app.store import learning

    t = _mk_track(fresh_db)
    t2 = learning.edit_track(t["id"], title="改名", goal="新目标", now=T0)
    assert t2["title"] == "改名" and t2["goal"] == "新目标"
    with pytest.raises(Exception):
        learning.edit_track("l99", title="x", now=T0)
    with pytest.raises(Exception):
        learning.edit_track(t["id"], title=" ", now=T0)


def test_track_lifecycle(fresh_db):
    from app.store import learning

    t = _mk_track(fresh_db)
    assert learning.set_track_status(t["id"], "paused")["status"] == "paused"
    assert learning.set_track_status(t["id"], "done")["status"] == "done"
    assert learning.set_track_status(t["id"], "active")["status"] == "active"
    with pytest.raises(Exception):
        learning.set_track_status(t["id"], "archived")
    with pytest.raises(Exception):
        learning.set_track_status("l99", "done")


def test_remove_track_cascades_points_and_notes(fresh_db):
    from app.store import learning

    t = _mk_track(fresh_db)
    _curriculum(fresh_db, t["id"], ["A", "B"])
    learning.submit_lesson_note(t["id"], "A", "第一课小结", now=T0)
    learning.remove_track(t["id"])
    with pytest.raises(Exception):
        learning.get_track(t["id"])
    assert learning.list_notes(t["id"]) == []
    with pytest.raises(Exception):
        learning.remove_track(t["id"])


def test_get_track_missing(fresh_db):
    from app.store import learning

    with pytest.raises(Exception):
        learning.get_track("l99")


# ---------- 大纲（set_curriculum：整体替换 + 同名继承）----------

def test_set_curriculum_creates_points_in_order(fresh_db):
    from app.store import learning

    t = _mk_track(fresh_db)
    _curriculum(fresh_db, t["id"], ["基础概念", "BEV 感知", "规划控制"])
    pts = learning.get_track(t["id"])["points"]
    assert [p["title"] for p in pts] == ["基础概念", "BEV 感知", "规划控制"]
    assert [p["id"] for p in pts] == ["k1", "k2", "k3"]
    assert all(p["status"] == "todo" for p in pts)
    assert pts[1]["ord"] == 1


def test_set_curriculum_replace_inherits_same_name(fresh_db):
    from app.store import learning

    t = _mk_track(fresh_db)
    _curriculum(fresh_db, t["id"], ["A", "B", "C"])
    b = _points(fresh_db, t["id"])["B"]
    learning.set_point_status(b["id"], "learned", now=T0)
    # 大纲调整：去掉 A/C，B 保留，新增 D
    learning.set_curriculum(t["id"], [{"title": "B"}, {"title": "D"}], now=T0)
    pts = _points(fresh_db, t["id"])
    assert set(pts) == {"B", "D"}
    assert pts["B"]["status"] == "learned"  # 同名继承
    assert pts["B"]["learned_at"] == T0
    assert pts["D"]["status"] == "todo"
    assert pts["B"]["id"] != b["id"]  # 替换语义：新行新 id


def test_set_curriculum_rejections(fresh_db):
    t = _mk_track(fresh_db)
    with pytest.raises(Exception):
        _curriculum(fresh_db, t["id"], [])  # 空大纲
    with pytest.raises(Exception):
        _curriculum(fresh_db, t["id"], ["A", "A"])  # 大纲内重名
    with pytest.raises(Exception):
        _curriculum(fresh_db, t["id"], ["  "])  # 空标题
    with pytest.raises(Exception):
        _curriculum(fresh_db, "l99", ["A"])  # track 不存在


def test_set_point_status_transitions(fresh_db):
    from app.store import learning

    t = _mk_track(fresh_db)
    _curriculum(fresh_db, t["id"], ["A"])
    a = _points(fresh_db, t["id"])["A"]
    p = learning.set_point_status(a["id"], "learned", now=T0)
    assert p["status"] == "learned" and p["learned_at"] == T0
    p = learning.set_point_status(a["id"], "revisit", now=T0)
    assert p["status"] == "revisit" and p["learned_at"] is None
    p = learning.set_point_status(a["id"], "todo", now=T0)
    assert p["status"] == "todo"
    with pytest.raises(Exception):
        learning.set_point_status(a["id"], "mastered", now=T0)  # 非法状态
    with pytest.raises(Exception):
        learning.set_point_status("k999", "learned", now=T0)  # 不存在


# ---------- 课程小结（追加式，不外键知识点）----------

def test_lesson_note_appends_with_title_snapshot(fresh_db):
    from app.store import learning

    t = _mk_track(fresh_db)
    _curriculum(fresh_db, t["id"], ["A"])
    learning.submit_lesson_note(t["id"], "A", "第一遍讲", now=T0)
    learning.submit_lesson_note(t["id"], "A", "回炉再讲", now=T0)
    notes = learning.list_notes(t["id"])
    assert len(notes) == 2
    assert all(n["point_title"] == "A" for n in notes)
    assert notes[0]["body_md"] == "回炉再讲"  # 新的在前


def test_curriculum_replace_keeps_notes(fresh_db):
    from app.store import learning

    t = _mk_track(fresh_db)
    _curriculum(fresh_db, t["id"], ["A", "B"])
    learning.submit_lesson_note(t["id"], "A", "A 的小结", now=T0)
    learning.set_curriculum(t["id"], [{"title": "B"}, {"title": "C"}], now=T0)  # A 被移除
    notes = learning.list_notes(t["id"])
    assert len(notes) == 1 and notes[0]["point_title"] == "A"  # 历史不随知识点消失


def test_lesson_note_rejections(fresh_db):
    from app.store import learning

    t = _mk_track(fresh_db)
    with pytest.raises(Exception):
        learning.submit_lesson_note(t["id"], "A", "  ", now=T0)  # 空正文
    with pytest.raises(Exception):
        learning.submit_lesson_note(t["id"], "", "x", now=T0)  # 空知识点标题
    with pytest.raises(Exception):
        learning.submit_lesson_note("l99", "A", "x", now=T0)  # track 不存在


def test_list_notes_limit(fresh_db):
    from app.store import learning

    t = _mk_track(fresh_db)
    for i in range(3):
        learning.submit_lesson_note(t["id"], "A", f"第{i}课", now=T0)
    notes = learning.list_notes(t["id"], limit=2)
    assert [n["body_md"] for n in notes] == ["第2课", "第1课"]


# ---------- 下一课判定与进度 ----------

def test_next_point_todo_first_in_ord(fresh_db):
    from app.store import learning

    t = _mk_track(fresh_db)
    _curriculum(fresh_db, t["id"], ["A", "B", "C"])
    pts = _points(fresh_db, t["id"])
    learning.set_point_status(pts["A"]["id"], "learned", now=T0)
    track = learning.get_track(t["id"])
    assert track["next_point"]["title"] == "B"
    assert track["progress"] == {"total": 3, "learned": 1, "todo": 2, "revisit": 0}


def test_next_point_revisit_when_no_todo(fresh_db):
    from app.store import learning

    t = _mk_track(fresh_db)
    _curriculum(fresh_db, t["id"], ["A", "B"])
    pts = _points(fresh_db, t["id"])
    learning.set_point_status(pts["A"]["id"], "learned", now=T0)
    learning.set_point_status(pts["B"]["id"], "revisit", now=T0)
    track = learning.get_track(t["id"])
    assert track["next_point"]["title"] == "B"  # 回炉优先于无 todo
    assert track["next_point"]["status"] == "revisit"


def test_next_point_none_when_all_learned(fresh_db):
    from app.store import learning

    t = _mk_track(fresh_db)
    _curriculum(fresh_db, t["id"], ["A"])
    pts = _points(fresh_db, t["id"])
    learning.set_point_status(pts["A"]["id"], "learned", now=T0)
    assert learning.get_track(t["id"])["next_point"] is None
