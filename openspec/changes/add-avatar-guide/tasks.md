# add-avatar-guide 任务

## 1. Red——契约测试先行

- [x] 1.1 `tests/test_mcp_contract.py` 新增 instructions 契约测试：`mcp.instructions` 非空、含 propose/approve 铁律关键词、含指路 `docs/avatar-guide.md`；跑 `uv run pytest tests/test_mcp_contract.py -q` 确认**失败**

## 2. Green——MCP 侧最小实现

- [x] 2.1 `app/mcp_server.py`：新增 `AVATAR_INSTRUCTIONS` 模块级常量（身份一句 + 门禁铁律三条 + 指路章程，见 design D2），`FastMCP("deputy", instructions=AVATAR_INSTRUCTIONS)`
- [x] 2.2 跑 1.1 测试确认通过；`uv run pytest -q` 全量确认无回归，守门测试原样绿

## 3. 章程文档（唯一真源）

- [x] 3.1 新增 `docs/avatar-guide.md`，按 design D3 七节结构写全（身份/三处地图/门禁铁律/feed-curator 关系三模式/工具地图 11 工具/SOP 索引/运维前置）；开头嵌与 `AVATAR_INSTRUCTIONS` 同构的铁律段

## 4. 部署文档瘦身

- [x] 4.1 重写 `docs/lobster-setup.md` §5：身份一句 + 铁律 + 指路章程（与 AVATAR_INSTRUCTIONS 同构），删除工具清单与处室细则内联
- [x] 4.2 修正 §4："6 个工具"改为"工具集以章程工具地图为准"

## 5. 收尾

- [x] 5.1 `uv run pytest -q` 全绿；通读四份产物自查 spec Scenario 全覆盖
