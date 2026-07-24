## ADDED Requirements

### Requirement: 看板展示项目 kind
看板的项目卡片 SHALL 展示该项目的 kind，让用户一眼区分商业项目（biz）与自用工具（tool）。该展示为只读，不提供在卡片上直接编辑 kind 的控件。

#### Scenario: 商业项目显示商业角标
- **WHEN** 渲染一个 kind 为 biz 的项目卡片
- **THEN** 卡片上出现"商业"角标（含 💰 标识）

#### Scenario: 自用工具显示工具角标
- **WHEN** 渲染一个 kind 为 tool 的项目卡片
- **THEN** 卡片上出现"工具"角标（含 🔧 标识）

#### Scenario: 卡片不提供 kind 编辑控件
- **WHEN** 查看项目卡片
- **THEN** 卡片上没有修改 kind 的下拉框或按钮（改 kind 走分身提议或其他入口）
