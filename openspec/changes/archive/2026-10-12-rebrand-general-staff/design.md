## Context

纯外观改版：标语、tab 分组与改名。无新依赖、无数据变化、无行为变更（skip_specs）。

## Goals / Non-Goals

只动 `index.html` 的静态文案与导航结构、CLAUDE.md / mcp_server docstring 措辞。不含讲武 tab（add-learning 引入）。

## Decisions

**D1 tab 分组用纯样式分组行，不引入嵌套组件** —— nav 在三处起点前插入小号分组标签（作战/军情/讲武），tab 本体保持现有平铺结构，改动最小且不碰 render 分派逻辑。

**D2 「问题」→「军情」只改 TABS 显示名** —— `window._tab` 的 key（questions）与路由、API 端点全部不动，避免牵连。

**D3 章程边界三件套写进 CLAUDE.md** —— 探索阶段与用户定稿的三条边界随本次措辞同步落章：①素材边界（军情处强依赖语料；讲武堂 自身→互联网→语料部分佐证）；②状态归属表（状态跟着实体走：奏折已阅/课程掌握归 deputy，原文已读收藏归 feed-curator，永不搬迁）；③军情处两模式（奏折进 deputy 存档，面圣即答不落档）。均为文档声明，无代码行为。

## Risks / Trade-offs

- [nav 变宽挤动布局] → 分组标签为行内小字，920px 容器内实测；溢出则换行可接受

## Migration Plan

无。回滚 = revert。

## Open Questions

无。
