# 评分模块增强方案（阶段 2）

目标：在阶段 1 的处理管线基础上，完善评分模型与配置能力，让运营可以可视化调整权重、阈值，并驱动榜单/标签/AI。

## 1. 指标体系

指标来源：`wallet_metrics` 表，基于 `fills`、`ledger`、`positions` 计算。拟扩展为六大维度：

| 维度 | 指标示例 |
| --- | --- |
| 收益能力 | 累计收益、年化收益、单位资金收益 |
| 风险控制 | 最大回撤、波动率、杠杆使用、强平距离 |
| 风险调整收益 | 夏普/卡玛比率、收益回撤比 |
| 交易质量 | 胜率、盈亏比、费用占比、滑点估算 |
| 稳定性 | 盈亏曲线平滑度、收益分布偏度、持仓时长一致性 |
| 资金效率 | 资金利用率、资金周转时间、存取款行为 |

每个指标写入 `wallet_metrics` 的 JSON 列（或扩展字段），便于前端展示详细数值。

## 2. 评分配置

采用 `system_configs` 存储 JSON：

- `scoring.dimensions`: 构成维度列表及权重（0-100，总和=100）。
  ```json
  {
    "return": {"weight": 30, "indicators": ["total_pnl", "annualized_return"]},
    "risk": {"weight": 20, "indicators": ["max_drawdown", "volatility"]},
    "risk_adjusted": {"weight": 15, "indicators": ["sharpe", "calmar"]},
    "trade_quality": {"weight": 15, "indicators": ["win_rate", "pl_ratio"]},
    "stability": {"weight": 10},
    "capital_efficiency": {"weight": 10}
  }
  ```
- `scoring.levels`: 等级阈值（S/A+/A/B/C）。
  ```json
  {"S": 90, "A+": 80, "A": 70, "B": 60}
  ```
- `scoring.auto_tags`: 规则列表（阈值表达式 → 标签）。

后台配置页读取/写入这些 key，提供验证（总权重大于 0、等级阈值递减、标签规则合法）。

## 3. 评分计算流程

1. **AI 模块** 仍然依赖最新 metrics。
2. `scoring.compute_metrics(address)`：
   - 先计算原始指标（收益、风险、费用等）。
   - 根据配置维度进行标准化（z-score 或 min-max）并加权汇总为总分。
   - 保存 `WalletMetric`（扩展 JSON 字段 `details`）与 `WalletScore`（含 `dimension_scores`、`level`）。
3. 自动标签：
   - 评分完成后读取 `scoring.auto_tags`，符合条件的标签写入 `wallet_tags`（type=system）。
   - 条件语法：`{"tag": "稳健型", "conditions": [{"indicator": "max_drawdown", "op": "<=", "value": 0.2}, ...]}`。

## 4. API / 前端需求

- `GET /api/scoring/config`：返回当前配置。
- `POST /api/scoring/config`：校验后写入 `system_configs`。支持“保存并触发重算”（调用队列对全部/筛选钱包 enqueue score job）。
- `GET /api/wallets/{address}/score_detail`: 返回 `dimension_scores`、指标详情、自动标签来源等，用于详情页展示。
- 榜单/列表读取 `dimension_scores`，提供按维度排序。

## 5. 实施步骤

1. 模型扩展：`wallet_metrics.details (JSON)`、`wallet_scores.dimension_scores (JSON)`、`wallet_tags` 自动写入。
2. `scoring` 服务改造：读取配置 → 计算指标 → 写入 JSON → 返回 detail。
3. API：新增 scoring-config 读写接口、wallet score detail API。
4. 前端后台配置页：可调整权重、阈值、标签规则，并显示维度说明；钱包列表/详情展示产出。

本方案完成后即可进入阶段 2 的编码：先实现配置读写和 scoring 函数，再补前端。
