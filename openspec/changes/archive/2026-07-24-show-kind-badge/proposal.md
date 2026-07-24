## Why

后端已支持改 kind（PR #3 合入），但看板卡片完全没展示 kind——用户区分不了哪些是商业项目、哪些是自用工具。kind 是用户项目的两大分类之一，值得"一眼可见"。

## What Changes

- 看板项目卡片头部，在项目名旁加一个轻量 kind 角标：`💰 商业` / `🔧 工具`。
- **只显示，不加下拉编辑**：kind 是极低频属性（项目性质基本定了不动），不占用高频界面。偶尔要改走分身提议或后续单独入口。
- 纯前端改动（`app/web/index.html`），后端 `get_state` 已返回 kind 字段，无需改。

## Capabilities

### New Capabilities
<!-- 无新 capability -->

### Modified Capabilities
- `project-management`: 已有 spec 只约束了 kind 的数据/修改，未涉及看板展示。本 change 增加"看板展示 kind"这条要求。

## Impact

- 代码：仅 `app/web/index.html`（卡片头部渲染 + 角标样式）。
- 无 API/store/MCP 改动，无 schema 变更，无破坏性。
- 验证：headless 渲染确认角标出现且 biz/tool 文案正确。
