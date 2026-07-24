## Context

看板卡片头部当前是：项目名 + stage 下拉 + 归档按钮（`app/web/index.html` 的 `renderBoard`）。`get_state` 返回的每个项目已含 `kind` 字段（biz/tool），前端只是没用它。

## Goals / Non-Goals

**Goals:**
- 卡片一眼能区分商业项目 / 自用工具。
- 极轻量，不增加交互复杂度。

**Non-Goals:**
- 不加 kind 下拉编辑（低频属性，不占高频界面）。
- 不动后端。

## Decisions

- 在项目名旁加一个 `<span class="kind-badge">`：kind==="biz" 显示 `💰 商业`，"tool" 显示 `🔧 工具`。
- 样式走已有 CSS 变量体系，弱化处理（小字号、灰底/描边），不与 stage 抢视觉重心。
- 归档项目照常显示角标（不特殊处理）。

## Risks / Trade-offs

- 风险极低：纯展示、纯前端。
- 唯一注意：卡片头部已有 name/stage-sel/归档按钮，加角标需确保窄屏不挤——用 flex 自然换行或小尺寸即可。
