## 1. 门面改版

- [x] 1.1 `app/web/index.html`：header 标语改「一号位的参谋部」（含状态行文案）；TABS 「问题」→「军情」；nav 加作战/军情/讲武三处分组标签（纯样式）；浏览器目检布局不挤
- [x] 1.2 `CLAUDE.md` 与 `app/mcp_server.py` docstring：自我介绍措辞换参谋部口径，并落章程边界三件套——素材边界（军情处强依赖 feed-curator；讲武堂 自身知识→互联网→语料部分佐证）、状态归属表（奏折已阅/课程掌握归 deputy，原文已读收藏归 feed-curator reading 表）、军情处两模式（奏折进 deputy；面圣微信即答不落档）
- [x] 1.3 `uv run pytest -q` 全绿（纯文案零行为）+ `openspec validate rebrand-general-staff` 通过
