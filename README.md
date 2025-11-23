# 钱包分析系统（Backend + Frontend）

后端采用 **Python + FastAPI**，内置配置加载、基础路由、健康检查与日志配置。后续将在此基础上接入 Hyperliquid 数据采集、评分、榜单、AI 分析等模块。

## 快速开始
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后访问 `http://127.0.0.1:8000/api/health` 获取健康状态。

### 前端启动
```bash
cd frontend
npm install
npm run dev
```
默认 `.env.development` 使用 `VITE_API_BASE_URL=http://localhost:8000/api`，上线后请根据绑定的域名修改该变量（避免在代码中写死地址）。

### 示例：导入钱包（当前为队列占位逻辑）
```bash
curl -X POST http://127.0.0.1:8000/api/wallets/import \
  -H "Content-Type: application/json" \
  -d '{
    "addresses": ["0x0000000000000000000000000000000000000000"],
    "tags": ["seed"],
    "dry_run": true
  }'
```
返回导入统计与每个地址的状态（当前仅做去重与占位，不落库）。

### 示例：同步钱包数据（调用 Hyperliquid 拉取原始数据并落库）
```bash
curl -X POST http://127.0.0.1:8000/api/wallets/sync \
  -H "Content-Type: application/json" \
  -d '{
    "address": "0x7fe8cfe481ec2f702692a9152e3f002f3e417ac6"
  }'
```
返回本次新增的 `fills` / `ledger` / `positions` 数量。默认从上次游标之后增量拉取。

### 查看游标与最新数据
```bash
# 游标
curl http://127.0.0.1:8000/api/wallets/status/0x7fe8cfe481ec2f702692a9152e3f002f3e417ac6

# 最新原始数据（默认 20 条）
curl http://127.0.0.1:8000/api/wallets/latest/0x7fe8cfe481ec2f702692a9152e3f002f3e417ac6

# 分页查询（带时间过滤）
curl "http://127.0.0.1:8000/api/wallets/fills?address=0x...&start_time=1700000000000&limit=100"

# 导出 CSV
curl -o fills.csv "http://127.0.0.1:8000/api/wallets/export/fills?address=0x...&limit=500"
curl -o ledger.csv "http://127.0.0.1:8000/api/wallets/export/ledger?address=0x..."

# 钱包列表 / 概览 / 详情
curl "http://127.0.0.1:8000/api/wallets?limit=20"
curl "http://127.0.0.1:8000/api/wallets/overview"
curl "http://127.0.0.1:8000/api/wallets/0x7fe8cfe481ec2f702692a9152e3f002f3e417ac6"

# 标签 / 榜单 / AI / 报表
curl http://127.0.0.1:8000/api/tags
curl http://127.0.0.1:8000/api/leaderboards
curl -X POST http://127.0.0.1:8000/api/wallets/0x.../ai
curl http://127.0.0.1:8000/api/reports/operations
# 刷新全部榜单（需管理员 Token）
curl -X POST -H "X-Admin-Token: change-admin-token" http://127.0.0.1:8000/api/leaderboards/run_all
```

## 目录结构（当前）
- `app/main.py`：FastAPI 入口，挂载路由。
- `app/core/config.py`：统一配置（环境变量 + 默认值）。
- `app/core/logging.py`：基础日志设置。
- `app/api/routes.py`：路由聚合。
- `app/api/endpoints/health.py`：健康检查与运行信息。
- `app/api/endpoints/wallets.py`：钱包导入、同步接口。
- `app/services/wallet_importer.py`：导入服务占位，将来挂任务队列/ETL。
- `app/services/hyperliquid_client.py`：Hyperliquid info API 轻量客户端。
- `app/services/etl.py`：同步 ledger / fills / positions / orders / portfolio 曲线，维护时间游标，含去重忽略。
- `app/services/query.py`：查询游标与最新原始数据、分页/导出。
- `app/services/task_queue.py`：RQ 队列封装，后台同步任务入口。
- `app/services/scoring.py`：基于成交计算简单指标与评分。
- `app/services/wallets_service.py`：钱包列表、详情、概览、同步状态维护。
- `app/services/admin.py`：RBAC（用户/角色/权限）、系统配置、审计日志。
- `app/services/tags.py`：标签体系管理、钱包打标。
- `app/services/leaderboard.py`：榜单定义与计算。
- `app/services/ai.py`：AI 分析/建议。
- `app/services/tasks_service.py` / `app/services/notifications.py`：任务日志、通知模板与订阅。
- `app/api/endpoints/admin.py`：后台管理接口（使用 `X-Admin-Token` 保护）。
- `app/api/endpoints/tags.py`：标签 CRUD 及钱包打标接口。
- `app/api/endpoints/leaderboards.py`：榜单列表/详情/刷新接口。
- `app/api/endpoints/ai.py`：AI 分析触发与查询。
- `app/api/endpoints/operations.py`：任务监控、通知管理、运营报表。
- `app/core/database.py`：SQLAlchemy 引擎与 Session 管理。
- `app/models/*.py`：SQLite 模型（wallets, ledger_events, fills, positions_snapshot, orders_history, portfolio_series, wallet_metrics, wallet_scores, tags, wallet_tags, leaderboards, leaderboard_results, ai_analysis, task_records, notification_* 等）。
- `frontend/`：React + Vite 前端工程（仪表盘、钱包列表/详情、榜单页、AI 展示）。
- `docs/PROGRESS.md`：阶段性里程碑记录。

### 后台队列（RQ）
- 配置 `REDIS_URL`（默认 redis://localhost:6379/0），启动 worker：
```bash
rq worker wallet-sync
```
- 通过 `/api/wallets/sync_async` 入队同步任务，返回 job_id。

### 管理后台接口（RBAC / 配置 / 审计）
- 设置 `ADMIN_API_TOKEN`（默认 `change-admin-token`），调用接口需在 Header 中携带 `X-Admin-Token`。
- 示例：
```bash
curl -H "X-Admin-Token: change-admin-token" http://127.0.0.1:8000/api/admin/users
```
- 支持用户、角色、权限 CRUD，系统配置、审计日志查询。

### 标签 / 榜单 / AI
- 标签管理：
```bash
curl http://127.0.0.1:8000/api/tags
curl -X POST -H "Content-Type: application/json" -H "X-Admin-Token: change-admin-token" \
  -d '{"name":"稳健型","type":"system","color":"#22d3ee"}' http://127.0.0.1:8000/api/tags
curl -X POST -H "Content-Type: application/json" -H "X-Admin-Token: change-admin-token" \
  -d '{"tag_ids":[1,2]}' http://127.0.0.1:8000/api/wallets/0x.../tags
```
- 榜单：
```bash
curl http://127.0.0.1:8000/api/leaderboards
curl -X POST -H "Content-Type: application/json" -H "X-Admin-Token: change-admin-token" \
  -d '{"name":"高收益榜","sort_key":"total_pnl","sort_order":"desc"}' http://127.0.0.1:8000/api/leaderboards
curl -X POST -H "X-Admin-Token: change-admin-token" http://127.0.0.1:8000/api/leaderboards/1/run
```
- AI 分析：
```bash
curl -X POST http://127.0.0.1:8000/api/wallets/0x.../ai
curl http://127.0.0.1:8000/api/wallets/0x.../ai
```

### 任务监控 / 通知 / 运营报表
- 运营概览（供前端使用，域名可通过 `VITE_API_BASE_URL` 配置）：
```bash
curl http://127.0.0.1:8000/api/reports/operations
```
- 任务列表 / 通知模板（需管理员 Token）：
```bash
curl -H "X-Admin-Token: change-admin-token" http://127.0.0.1:8000/api/tasks
curl -X POST -H "Content-Type: application/json" -H "X-Admin-Token: change-admin-token" \
  -d '{"name":"任务完成提醒","channel":"email","content":"{{wallet}} 已完成同步"}' http://127.0.0.1:8000/api/notifications/templates
curl -X POST -H "Content-Type: application/json" -H "X-Admin-Token: change-admin-token" \
  -d '{"recipient":"ops@example.com","template_id":1}' http://127.0.0.1:8000/api/notifications/subscriptions
- 调度配置（需管理员 Token）：
```bash
curl -H "X-Admin-Token: change-admin-token" http://127.0.0.1:8000/api/schedules
curl -X POST -H "Content-Type: application/json" -H "X-Admin-Token: change-admin-token" \
  -d '{"name":"每小时刷新榜单","job_type":"leaderboard_run_all","cron":"0 * * * *"}' http://127.0.0.1:8000/api/schedules
```

如需在榜单 Top 变化时自动通知，可在系统配置表中写入：
- `leaderboard_notify_template`: 通知模板 ID（整数，需已存在模板）
- `leaderboard_notify_recipient`: 邮箱或 Webhook 地址。  
刷新榜单时若 Top 发生变化将触发通知。

### 用户偏好 / 前端设置
- 后台接口（需管理员 Token）：
```bash
curl -H "X-Admin-Token: change-admin-token" "http://127.0.0.1:8000/api/admin/preferences?email=user@example.com"
curl -X POST -H "Content-Type: application/json" -H "X-Admin-Token: change-admin-token" \
  -d '{"default_period":"30d","favorite_wallets":["0x..."]}' \
  "http://127.0.0.1:8000/api/admin/preferences?email=user@example.com"
```
- 前端 `/settings` 页面提供可视化配置，会将结果缓存到浏览器并驱动钱包/榜单默认排序、收藏展示。

## 下一步（建议）
1) 设计数据库模型（SQLite）与迁移脚本；拆分原始数据表与规范化表。  
2) 编写 Hyperliquid 数据采集器（分页续拉、幂等防重），落库原始流水。  
3) 引入任务队列（RQ/Celery）与任务状态表，支撑导入、评分、榜单、AI 分析。  
4) 定义指标与评分配置 Schema（权重、阈值），实现增量计算服务。  
5) 前台接口：钱包列表/详情、榜单、标签、AI 结果、通知订阅。  
6) 系统管理：RBAC、操作日志、配置管理、缓存清理接口。  
