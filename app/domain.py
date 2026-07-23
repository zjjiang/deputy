"""领域常量与规则 —— 从旧原型移植，唯一"业务真理"来源。

两轴 + 类型：
  stage 生命周期状态机：spark→probe→attack→operate→maintain，任意→frozen/archived
  drive 谁在推：self(自攻)/assist(助攻)/auto(自动)
  kind  类型：biz(商业)/tool(自用工具)
"""
from __future__ import annotations

VALID_STAGES: frozenset[str] = frozenset(
    {"spark", "probe", "attack", "operate", "maintain", "frozen", "archived"}
)
VALID_DRIVES: frozenset[str] = frozenset({"self", "assist", "auto"})
VALID_KINDS: frozenset[str] = frozenset({"biz", "tool"})

# 状态机：每个状态允许迁移到哪些状态。
# 主线 spark→probe→attack→operate→maintain；任何状态都能被雪藏或归档；
# 雪藏可解冻回验证/主攻；归档是终态（需 unarchive 专门放开）。
STAGE_TRANSITIONS: dict[str, frozenset[str]] = {
    "spark": frozenset({"probe", "frozen", "archived"}),
    "probe": frozenset({"attack", "frozen", "archived", "spark"}),
    "attack": frozenset({"operate", "frozen", "archived", "probe"}),
    "operate": frozenset({"maintain", "frozen", "archived"}),
    "maintain": frozenset({"operate", "frozen", "archived"}),
    "frozen": frozenset({"probe", "attack", "spark", "archived"}),
    "archived": frozenset(),
}

STAGE_LABELS: dict[str, str] = {
    "spark": "💡 火花",
    "probe": "🔬 验证",
    "attack": "🔨 主攻",
    "operate": "💰 运营",
    "maintain": "🌱 维护",
    "frozen": "❄️ 雪藏",
    "archived": "⚰️ 归档",
}
DRIVE_LABELS: dict[str, str] = {
    "self": "🙋 自攻",
    "assist": "🤝 助攻",
    "auto": "🤖 自动",
}
KIND_LABELS: dict[str, str] = {"biz": "商业项目", "tool": "自用工具"}

# ---- 门禁：提议动作白名单 ----
# 分身只能提议这些动作；approve 时按此派发到 store.projects 的写函数。
# 每个 action 声明它需要的参数键，写操作前做校验。
PROPOSAL_ACTIONS: dict[str, tuple[str, ...]] = {
    "set_focus": ("summary", "items"),
    "add_todo": ("project_id", "text"),
    "toggle_todo": ("project_id", "todo_id", "done"),
    "edit_todo": ("project_id", "todo_id", "text"),
    "remove_todo": ("project_id", "todo_id"),
    "set_stage": ("project_id", "stage"),
    "set_drive": ("project_id", "drive"),
    "set_trigger": ("project_id", "trigger"),
    "add_project": ("name", "stage", "drive", "kind"),
    "rename_project": ("project_id", "name"),
    "add_to_backlog": ("text",),
}


class DomainError(ValueError):
    """业务规则违反（非法状态、非法迁移等），映射成 400。"""
