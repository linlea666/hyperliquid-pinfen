# 新增代码审查发现

## 1. 队列服务缺失 `logging` 导致模块导入失败
- 位置：`app/services/task_queue.py`
- 问题：文件内多处使用 `logger = logging.getLogger(__name__)` 和 `logger.info(...)`，但顶部没有 `import logging`，模块加载即会抛出 `NameError`。调度/同步 worker 启动时会直接失败，所有队列任务无法投递或执行。
- 建议：补充 `import logging` 并为关键路径加上异常隔离，避免日志初始化问题影响任务执行。

## 2. 任务日志服务缺少必要依赖，所有调用都会抛 `NameError`
- 位置：`app/services/tasks_service.py`
- 问题：函数体大量使用 `Optional`、`List`、`json`、`datetime`、`time`、`select`、`func` 等对象，但文件顶部只导入了 `OperationalError` 与数据库模型。任何调用 `log_task_start`/`log_task_end` 等方法都会因为缺失导入而报错，任务执行记录、AI 日志记录全都无法写入。
- 建议：补充类型/工具模块与 SQLAlchemy 选择函数的导入；同时考虑在 `_with_retry` 中限制锁粒度，避免长时间占用全局写锁。
