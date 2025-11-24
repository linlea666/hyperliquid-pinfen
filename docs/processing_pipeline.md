# 钱包分析处理管线设计（阶段 1）

本文档梳理“导入 → 数据同步 → 指标评分 → AI 分析”的状态流、数据结构与 API 规划，为后续编码实现提供 blueprint。

## 1. 总体思路

- **导入接口轻量化**：只负责去重落库、写入初始状态，不做 heavy 计算。
- **任务队列串联流程**：同步、评分、AI 分析都以 RQ 任务形式运行，互相串联/重试。
- **状态可观测**：`wallets` 表保存阶段状态 & 最近时间戳，`wallet_processing_logs` 记录明细，运营面板可查看并重试。
- **可配置调度**：通过 `system_config` 配置批次、并发、重算周期，由 APScheduler 按规则投递任务。

## 2. 数据模型变更

### 2.1 wallets 表新增字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `sync_status` | String(16) | `pending/running/synced/failed` |
| `score_status` | String(16) | `pending/running/scored/failed` |
| `ai_status` | String(16) | `pending/running/completed/failed` |
| `last_sync_at` | DateTime | 最近同步完成时间 |
| `last_score_at` | DateTime | 最近评分完成时间 |
| `last_ai_at` | DateTime | 最近 AI 分析时间 |
| `next_score_due` | DateTime | 下一次评分截止（便于调度） |
| `last_error` | Text | 最近失败原因摘要（可选） |

### 2.2 wallet_processing_logs（新表）

记录每次处理流水（便于审计与重试）。字段：

- `id` (PK)
- `wallet_address`
- `stage` (`sync` / `score` / `ai`)
- `status` (`pending/running/success/failed`)
- `payload` / `result` / `error`
- `attempt`（第几次执行）
- `scheduled_by`（触发来源：import/manual/cron/trigger）
- `started_at`, `finished_at`, `created_at`

### 2.3 system_config 新 Key

| Key | 示例 | 说明 |
| --- | --- | --- |
| `processing.max_parallel_sync` | `5` | worker 同时跑的同步任务数 |
| `processing.max_parallel_score` | `5` | 同上 |
| `processing.retry_limit` | `3` | 每个阶段重试次数 |
| `processing.retry_delay_seconds` | `600` | 失败后多久重投 |
| `processing.rescore_period_days` | `7` | 定期重算，计算 `next_score_due` 用 |
| `processing.rescore_trigger_pct` | `5` | 如收益/回撤变化超阈值，立即入队 |
| `processing.ai_period_days` | `30` | AI 分析刷新周期 |

## 3. 状态流

```
导入成功 → sync_status=pending → enqueue(sync)
sync running → 成功: sync_status=synced + last_sync_at 更新 + enqueue(score)
             → 失败: sync_status=failed + last_error，等待重试
score running → 成功: score_status=scored + last_score_at + next_score_due + enqueue(ai)
             → 失败: score_status=failed
ai running → 成功: ai_status=completed + last_ai_at
          → 失败: ai_status=failed
```

定时任务：

- 每日巡检 `next_score_due` 到期的钱包，入队 `score`。
- 根据运行指标（收益/回撤/资金变动）触发 `score`/`ai` 重算。

## 4. 队列与任务

| Job Type | 触发 | 输入 | 输出 / 影响 |
| --- | --- | --- | --- |
| `wallet_sync` | 导入、定时、手动 | `address` + optional end_time | 从 Hyperliquid 拉 ledger/fills/positions/orders，更新状态与游标 |
| `wallet_score` | sync 成功、定时、触发 | `address` | 调 `scoring.compute_metrics`，写 `wallet_metrics`/`wallet_scores` |
| `wallet_ai` | score 成功、定时 | `address` | 写 `ai_analysis` |

任务执行模板：

1. `log = wallet_processing_logs.create(stage='sync', status='running', ...)`
2. 运行核心逻辑，捕获异常。
3. 更新 `log.status`、`wallet.sync_status` 等字段。
4. 若成功且需要后续任务 → enqueue 下一个 job。
5. 若失败 → 记录 error，判断是否超过重试上限，必要时写通知。

## 5. API / 后台扩展规划

- `GET /api/wallets/status/{address}`：返回三阶段状态、时间戳、最近错误、排队情况。
- `GET /api/wallets/jobs?stage=sync&status=pending`：分页查询 `wallet_processing_logs`。
- `POST /api/wallets/{address}/tasks/{stage}/retry`：手动重跑某阶段。
- 运维面板新增“分析处理”模块，展示队列长度、失败列表、按阶段统计。
- 设置页新增“分析处理配置”表单，对应 system_config 的 key。

## 6. 实施顺序

1. 修改模型（wallet 字段 + 新日志表）和 Alembic/SQLite 初始化。
2. 更新服务层：状态更新函数、日志写入、RQ 队列封装。
3. 扩展 API 与运维面板。
4. 增加调度任务（APScheduler）定期扫描待处理钱包。

以上设计完成后，进入阶段 2（实际实现）。

