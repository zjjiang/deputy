## Context

`editTodo(pid,tid,old)` 函数、`/api/todo/edit` 端点、`store.edit_todo` 全部存在——之前只删了 projectCard 里那个 `<span class="mini">改</span>` 的 HTML。

## Goals / Non-Goals

**Goals:** 恢复 todo 行的"改"入口。

**Non-Goals:** 不改后端/API；不改交互方式（仍用 prompt 弹窗改文字，与其他操作一致）。

## Decisions

- 在 projectCard 的 todo 行，"×"删除按钮前加回 `<span class="mini" onclick="editTodo(...)">改</span>`。
- 位置：文字/完成日期之后、删除之前，与移除前一致。

## Risks / Trade-offs

- 无风险，纯前端恢复。上次移除是判断失误（低估了改字需求），本次修正。
