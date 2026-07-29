## Why

之前重设计时移除了 todo 的"改"按钮，理由是"删了重加更直接"。实际使用发现：改错字、补充内容时，删了重加会丢 todo 的完成状态和 done_at，且比直接改麻烦。改 todo 是真实需求，入口应恢复。

## What Changes

- 看板 todo 行恢复"改"入口（复用已存在的前端 `editTodo()` 函数）。
- 后端 `edit_todo`、API `/api/todo/edit`、前端函数均已存在，本 change 仅恢复按钮的 HTML。

## Capabilities

### Modified Capabilities
- `project-management`: 看板展示规范增加"提供修改 todo 文字的入口"。

## Impact

- 代码：仅 `app/web/index.html`（projectCard 的 todo 行加回"改"span）。
- 无后端/API/schema 改动（能力早已存在，仅前端入口）。
- 验证：node --check + 手动确认按钮出现且能改。
