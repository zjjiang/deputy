"""store 包：决策中枢的持久层。

- db        SQLite 连接 + schema
- projects  真源读写（项目/todo/需求池/聚焦）+ 业务规则
- questions 预设问题读写（问题配置 + 版本化回答）+ 到期/校验规则
- proposals 门禁队列（分身提议 → 用户批准 → 派发执行）
"""
from . import db, projects, proposals, questions

__all__ = ["db", "projects", "proposals", "questions"]
