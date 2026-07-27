## MODIFIED Requirements

### Requirement: 看板展示项目 kind
看板的项目卡片 SHALL 展示该项目的 kind，让用户一眼区分商业项目（biz）与自用工具（tool）。该展示为只读且 SHALL 使用纯文字标签（"商业" / "工具"），不使用 emoji 图标，不提供在卡片上直接编辑 kind 的控件。

#### Scenario: 商业项目显示商业角标
- **WHEN** 渲染一个 kind 为 biz 的项目卡片
- **THEN** 卡片上出现纯文字"商业"角标（无 emoji 标识）

#### Scenario: 自用工具显示工具角标
- **WHEN** 渲染一个 kind 为 tool 的项目卡片
- **THEN** 卡片上出现纯文字"工具"角标（无 emoji 标识）

#### Scenario: 卡片不提供 kind 编辑控件
- **WHEN** 查看项目卡片
- **THEN** 卡片上没有修改 kind 的下拉框或按钮（改 kind 走分身提议或其他入口）

## ADDED Requirements

### Requirement: 界面不使用装饰性 emoji
看板界面 SHALL 不使用装饰性 emoji 表达状态、分区或操作，改用文字标签、语义色与排版层级。通用无歧义符号（如勾选 ✓、删除 ×）不受此限。

#### Scenario: 项目状态以文字呈现
- **WHEN** 渲染项目卡片的状态选择器
- **THEN** 各状态选项为纯文字（火花/验证/主攻/运营/维护/雪藏/归档），不含 emoji

#### Scenario: 分区标题以文字呈现
- **WHEN** 渲染 tab 栏与各分区（全盘/门禁/需求池、此刻聚焦）
- **THEN** 标题为纯文字，不含 emoji 图标
