export interface WalletPeriodStat {
  pnl: number;
  return: number;
  trades: number;
}

export interface WalletMetricDetails {
  total_pnl?: number;
  total_fees?: number;
  avg_pnl?: number;
  win_rate?: number;
  max_drawdown?: number;
  volume?: number;
  trades?: number;
  equity_stability?: number;
  capital_efficiency?: number;
  periods?: Record<string, WalletPeriodStat>;
}

export interface WalletMetric {
  trades?: number;
  wins?: number;
  losses?: number;
  win_rate?: string;
  total_pnl?: string;
  total_fees?: string;
  volume?: string;
  max_drawdown?: string;
  avg_pnl?: string;
  as_of?: number;
  updated_at?: string;
  details?: WalletMetricDetails;
}

export interface TagSummary {
  id?: number;
  name: string;
  type?: string;
  color?: string;
  icon?: string;
}

export interface TagRuleCondition {
  field: string;
  op: string;
  value: number | string;
  source?: 'metric' | 'portfolio';
  period?: string;
}

export interface TagResponse extends TagSummary {
  description?: string;
  parent_id?: number;
  rule?: TagRuleCondition[] | Record<string, any> | null;
}

export interface TagPayload {
  id?: number;
  name: string;
  type: string;
  color: string;
  icon?: string;
  description?: string;
  parent_id?: number;
  rule: TagRuleCondition[] | null;
}

export interface WalletSummary {
  address: string;
  status: string;
  sync_status?: string;
  score_status?: string;
  ai_status?: string;
  tags: TagSummary[];
  source: string;
  last_synced_at?: string;
  last_score_at?: string;
  last_ai_at?: string;
  next_score_due?: string;
  next_sync_due?: string;
  next_ai_due?: string;
  last_error?: string;
  note?: string | null;
  created_at: string;
  first_trade_time?: string;
  active_days?: number;
  metric?: WalletMetric;
  metric_period?: string;
  portfolio?: Record<string, PortfolioStats>;
  score?: {
    score: string;
    level: string;
  };
}

export interface WalletListResponse {
  total: number;
  items: WalletSummary[];
}

export interface WalletNoteResponse {
  address: string;
  note?: string | null;
}

export interface PortfolioStats {
  return_pct?: string;
  max_drawdown_pct?: string;
  volume?: string;
  updated_at?: string;
}

export interface WalletOverview {
  total_wallets: number;
  synced_wallets: number;
  pending_wallets: number;
  running_wallets: number;
  failed_wallets: number;
  ledger_events: number;
  fills: number;
  last_sync?: string;
}

export interface LatestRecords {
  ledger: any[];
  fills: any[];
  positions: any[];
  orders: any[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
}

export interface LeaderboardResponse {
  id: number;
  name: string;
  type: string;
  description?: string;
  icon?: string;
  style: string;
  accent_color: string;
  badge?: string;
  filters?: any[];
  sort_key: string;
  sort_order: string;
  period: string;
  is_public: boolean;
  result_limit: number;
  auto_refresh_minutes: number;
}

export interface LeaderboardResultEntry {
  wallet_address: string;
  rank: number;
  score?: string;
  metrics?: Record<string, any>;
}

export interface LeaderboardResultResponse {
  leaderboard: LeaderboardResponse;
  results: LeaderboardResultEntry[];
}

export interface AIAnalysisResponse {
  wallet_address: string;
  version: string;
  score?: number;
  style?: string;
  strengths?: string;
  risks?: string;
  suggestion?: string;
  follow_ratio?: number;
  created_at: string;
}

export interface TaskRecord {
  id: number;
  task_type: string;
  status: string;
  payload?: string;
  result?: string;
  error?: string;
  started_at: string;
  finished_at?: string;
}

export interface TaskListResponse {
  items: TaskRecord[];
}

export interface OperationsReport {
  wallet_total: number;
  synced_wallets: number;
  ledger_events: number;
  fills: number;
  tasks_running: number;
  tasks_failed: number;
  notifications_sent: number;
  last_sync?: string;
}

export interface Schedule {
  id: number;
  name: string;
  job_type: string;
  cron: string;
  payload?: Record<string, any>;
  enabled: boolean;
}

export interface PreferenceResponse {
  default_period: string;
  default_sort: string;
  theme: string;
  favorite_wallets: string[];
  favorite_leaderboards: number[];
}

export interface TemplateResponse {
  id: number;
  name: string;
  channel: string;
  subject?: string;
  content: string;
  description?: string;
}

export interface SubscriptionResponse {
  id: number;
  recipient: string;
  template_id: number;
  enabled: boolean;
}

export interface WalletImportResult {
  address: string;
  status: string;
  message?: string;
  tags_applied: string[];
  job_id?: string;
}

export interface WalletImportResponse {
  requested: number;
  imported: number;
  skipped: number;
  dry_run: boolean;
  results: WalletImportResult[];
  source: string;
  tags: string[];
  created_by?: string;
  created_at?: string;
}

export interface WalletImportHistoryEntry {
  id: number;
  source: string;
  tags: string[];
  created_by?: string;
  created_at: string;
}

export interface WalletImportHistoryResponse {
  total: number;
  items: WalletImportHistoryEntry[];
}

export interface ProcessingLog {
  id: number;
  wallet_address: string;
  stage: string;
  status: string;
  attempt: number;
  scheduled_by: string;
  payload?: string;
  result?: string;
  error?: string;
  started_at?: string;
  finished_at?: string;
  created_at: string;
}

export interface ProcessingLogListResponse {
  items: ProcessingLog[];
}

export interface ProcessingStageStats {
  stage: string;
  counts: Record<string, number>;
}

export interface ProcessingScopeInfo {
  type: string;
  recent_days?: number;
  tag?: string;
  description: string;
}

export interface ProcessingSummaryResponse {
  stages: ProcessingStageStats[];
  pending_rescore: number;
  pending_wallets: number;
  queue_size: number;
  batch_estimate_seconds: number;
  scope: ProcessingScopeInfo;
  last_failed: ProcessingLog[];
}

export interface ScoringIndicatorConfig {
  field: string;
  min: number;
  max: number;
  higher_is_better: boolean;
  weight: number;
}

export interface ScoringDimensionConfig {
  key: string;
  name: string;
  weight: number;
  indicators: ScoringIndicatorConfig[];
}

export interface ScoringLevelConfig {
  level: string;
  min_score: number;
}

export interface ScoringConfig {
  dimensions: ScoringDimensionConfig[];
  levels: ScoringLevelConfig[];
}

export interface ScoringConfigResponse {
  config: ScoringConfig;
}

export interface ProcessingConfig {
  max_parallel_sync: number;
  max_parallel_score: number;
  retry_limit: number;
  retry_delay_seconds: number;
  rescore_period_days: number;
  rescore_trigger_pct: number;
  ai_period_days: number;
  scope_type: string;
  scope_recent_days: number;
  scope_tag: string;
  batch_size: number;
  batch_interval_seconds: number;
  request_rate_per_min: number;
  sync_cooldown_days: number;
  score_cooldown_days: number;
  ai_cooldown_days: number;
  portfolio_refresh_hours: number;
}

export interface ProcessingTemplate {
  key: string;
  name: string;
  description: string;
  overrides: Record<string, string | number>;
}

export interface ProcessingConfigResponse {
  config: ProcessingConfig;
  templates: ProcessingTemplate[];
  active_template?: string;
}

export interface ProcessingBatchResponse {
  requested: number;
  enqueued: number;
  skipped: number;
}
