## 1. 重写样式

- [x] 1.1 重定义 :root 配色（中性灰阶 + 单强调靛蓝 + 语义色），去掉所有 linear-gradient。
- [x] 1.2 加 --mono 等宽字体变量，应用于项目ID/提议#编号/时间/args。
- [x] 1.3 卡片：左竖线按状态取语义色，主攻最重、其余安静。

## 2. 去 emoji + 文案

- [x] 2.1 STAGES / TABS / 焦点 / 门禁 / 需求池 / 空态 / kind 角标：去除全部装饰 emoji，改纯文字。
- [x] 2.2 保留 ✓（勾选）、×（删除/驳回）；new project、focus、trigger 等入口改文字。

## 3. 验证

- [x] 3.1 node --check 抽出的内联 JS 语法通过。
- [x] 3.2 headless 渲染确认三 tab 正常、状态/kind 以文字呈现、无残留装饰 emoji。

## 4. 收尾

- [ ] 4.1 开分支 → PR → 合 main。
- [ ] 4.2 归档 change。
