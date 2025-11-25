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
}

export interface TagSummary {
  id?: number;
  name: string;
  type?: string;
  color?: string;
  icon?: string;
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
  last_error?: string;
  created_at: string;
  metric?: WalletMetric;
  metric_period?: string;
  score?: {
    score: string;
    level: string;
  };
}

export interface WalletListResponse {
  total: number;
  items: WalletSummary[];
}

export interface WalletOverview {
  total_wallets: number;
  synced_wallets: number;
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

export interface LeaderboardResponse {
  id: number;
  name: string;
  type: string;
  description?: string;
  icon?: string;
  style: string;
  accent_color: string;
  badge?: string;
  filters?: Record<string, any>;
  sort_key: string;
  sort_order: string;
  period: string;
  is_public: boolean;
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
