## Why

当前看板到处用 emoji 当图标（🎯🚪💡🔨💰🔬🌱❄️⚰️🔓 等），显得花哨、不正经，且 emoji 在替本该由排版/颜色/留白承担的工作。用户要求去掉这些 emoji、做得克制专业。

## What Changes

- **去掉所有装饰性 emoji**，改用中文文字标签 + 语义色 + 排版层级来表达信息。
- **视觉方向：克制的"操作台"风格**——呼应"决策中枢"身份，而非又一个花哨 SaaS 看板：
  - 单一强调色（靛蓝）+ 中性灰阶，去掉所有 linear-gradient。
  - 编号/项目ID/时间/提议编号用等宽字体（signature）。
  - 项目状态从"emoji+下拉"保留下拉但选项改纯文字；卡片左侧语义色竖线表状态，主攻最重、其余安静。
  - 门禁区是唯一视觉重点（deputy 区别于普通看板的灵魂）。
- 保留通用无歧义符号：勾选用 ✓、删除用 ×。
- 纯前端改动（`app/web/index.html`），行为/API 不变。

## Capabilities

### Modified Capabilities
- `project-management`: 已有"看板展示 kind"要求含 emoji 角标；本 change 改为纯文字标签，并整体确立"界面不使用装饰性 emoji"的展示规范。

## Impact

- 代码：仅 `app/web/index.html`（样式 + 渲染函数中的图标/文案）。
- 无 API/store/MCP/schema 改动，行为完全不变。
- 验证：node --check 语法 + headless 渲染确认三个 tab 正常、无残留装饰 emoji、状态/kind 以文字呈现。
