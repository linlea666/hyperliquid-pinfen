import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGet, apiPost, apiPut } from '../api/client';
import { showToast } from '../utils/toast';
import type {
  Schedule,
  TemplateResponse,
  SubscriptionResponse,
  PreferenceResponse,
  ScoringConfigResponse,
  ScoringConfig,
  ProcessingConfigResponse,
  ProcessingConfig,
  ProcessingBatchResponse,
  ProcessingTemplate,
  LeaderboardResponse,
} from '../types';

type AdminTab = 'notifications' | 'schedules' | 'preferences' | 'processing' | 'scoring' | 'leaderboards';

interface LeaderboardDraft
  extends Omit<LeaderboardResponse, 'id' | 'filters'> {
  id?: number;
  filters: any[];
  filtersText: string;
}

const defaultLeaderboardDraft: LeaderboardDraft = {
  name: '',
  type: 'custom',
  description: '',
  icon: '',
  style: 'table',
  accent_color: '#7c3aed',
  badge: '',
  filters: [],
  filtersText: '[]',
  sort_key: 'total_pnl',
  sort_order: 'desc',
  period: 'month',
  is_public: true,
  result_limit: 20,
  auto_refresh_minutes: 0,
};

export default function AdminPanel() {
  const [email, setEmail] = useState('');
  const [activeTab, setActiveTab] = useState<AdminTab>('notifications');

  const { data: templates, refetch: refetchTemplates } = useQuery<TemplateResponse[]>({
    queryKey: ['admin-templates'],
    queryFn: () => apiGet<TemplateResponse[]>('/notifications/templates'),
  });

  const { data: subs, refetch: refetchSubs } = useQuery<SubscriptionResponse[]>({
    queryKey: ['admin-subs'],
    queryFn: () => apiGet<SubscriptionResponse[]>('/notifications/subscriptions'),
  });

  const { data: schedules, refetch: refetchSchedules } = useQuery<Schedule[]>({
    queryKey: ['admin-schedules'],
    queryFn: () => apiGet<Schedule[]>('/schedules'),
  });

  const [newTemplate, setNewTemplate] = useState({ name: '', channel: 'email', subject: '', content: '' });
  const [newSub, setNewSub] = useState({ template_id: '', recipient: '' });
  const [newSchedule, setNewSchedule] = useState({ name: '', job_type: 'leaderboard_run_all', cron: '0 * * * *', address: '' });
  const [prefs, setPrefs] = useState<PreferenceResponse | null>(null);
  const { data: scoringConfigResp, refetch: refetchScoringConfig } = useQuery<ScoringConfigResponse>({
    queryKey: ['scoring-config'],
    queryFn: () => apiGet<ScoringConfigResponse>('/scoring/config'),
  });
  const { data: processingConfigResp, refetch: refetchProcessingConfig } = useQuery<ProcessingConfigResponse>({
    queryKey: ['processing-config'],
    queryFn: () => apiGet<ProcessingConfigResponse>('/processing/config'),
  });
  const [scoringDraft, setScoringDraft] = useState<ScoringConfig | null>(null);
  const [triggerRescore, setTriggerRescore] = useState(false);
  const [processingDraft, setProcessingDraft] = useState<ProcessingConfig | null>(null);
  const [activeProcessingTemplate, setActiveProcessingTemplate] = useState<string | null>(null);
  const [runningBatch, setRunningBatch] = useState(false);
  const { data: adminLeaderboards, refetch: refetchAdminLeaderboards } = useQuery<LeaderboardResponse[]>({
    queryKey: ['admin-leaderboards'],
    queryFn: () => apiGet<LeaderboardResponse[]>('/leaderboards'),
  });
  const [leaderboardDraft, setLeaderboardDraft] = useState<LeaderboardDraft | null>(null);
  const [savingLeaderboard, setSavingLeaderboard] = useState(false);
  const indicatorMeta: Record<string, string> = {
    total_pnl: '单位：USDC，统计周期内的累计收益额',
    avg_pnl: '单位：USDC/笔，单笔平均盈亏',
    win_rate: '0-1（或百分比）之间的胜率值',
    trades: '成交笔数，衡量活跃程度',
    max_drawdown: '最大回撤，建议填负值区间',
    volume: '成交额（USDC），衡量资金效率',
    equity_stability: '权益稳定性分布（0-1）',
    capital_efficiency: '资金效率指标（0-1）',
    funding_cost_ratio: '资金费支出占总收益的比例，越低越好',
    effective_fee_cross: '当前永续 taker 手续费率，越低越好',
    portfolio_return_30d: '官方 Portfolio 统计的 30 日收益率',
    portfolio_max_drawdown_30d: '官方 30 日最大回撤，越低越好',
  };
  const dimensionHints: Record<string, string> = {
    profit: '衡量收益能力，越高越好',
    risk: '衡量风险控制，回撤越小越高',
    risk_adjusted: '收益/风险匹配程度',
    trades: '成交质量与活跃度',
    stability: '权益曲线平滑程度',
    capital: '资金使用效率',
    cost: '资金费用、手续费等成本控制能力',
    portfolio: '参考官方 Portfolio 曲线的表现',
  };

  useEffect(() => {
    if (scoringConfigResp) {
      setScoringDraft(JSON.parse(JSON.stringify(scoringConfigResp.config)));
    }
  }, [scoringConfigResp]);

  useEffect(() => {
    if (processingConfigResp) {
      setProcessingDraft(JSON.parse(JSON.stringify(processingConfigResp.config)));
      setActiveProcessingTemplate(processingConfigResp.active_template ?? null);
    }
  }, [processingConfigResp]);

  useEffect(() => {
    if (!adminLeaderboards || adminLeaderboards.length === 0) return;
    if (leaderboardDraft && leaderboardDraft.id) return;
    const first = adminLeaderboards[0];
    setLeaderboardDraft({
      ...first,
      filters: Array.isArray(first.filters) ? first.filters : [],
      filtersText: JSON.stringify(first.filters ?? [], null, 2),
    });
  }, [adminLeaderboards]);

  const loadPrefs = async () => {
    if (!email) return;
    const data = await apiGet<PreferenceResponse>(`/admin/preferences?email=${encodeURIComponent(email)}`);
    setPrefs(data);
    showToast('已加载用户偏好', 'success');
  };

  const savePrefs = async () => {
    if (!email || !prefs) return;
    await apiPost(`/admin/preferences?email=${encodeURIComponent(email)}`, prefs);
    showToast('用户偏好已保存', 'success');
  };

  const updateScoringDraft = (updater: (draft: ScoringConfig) => void) => {
    setScoringDraft((prev) => {
      if (!prev) return prev;
      const next = JSON.parse(JSON.stringify(prev)) as ScoringConfig;
      updater(next);
      return next;
    });
  };

  const updateProcessingDraft = (updater: (draft: ProcessingConfig) => void) => {
    setProcessingDraft((prev) => {
      if (!prev) return prev;
      const next = { ...prev };
      updater(next);
      return next;
    });
  };

  const applyProcessingTemplate = (template: ProcessingTemplate) => {
    if (!processingDraft) return;
    updateProcessingDraft((draft) => {
      Object.entries(template.overrides || {}).forEach(([key, value]) => {
        if (value !== undefined && key in draft) {
          (draft as Record<string, any>)[key] = value as any;
        }
      });
    });
    setActiveProcessingTemplate(template.key);
    showToast(`已应用模板「${template.name}」`, 'success');
  };

  const saveScoringConfig = async () => {
    if (!scoringDraft) return;
    await apiPost('/scoring/config', { config: scoringDraft, trigger_rescore: triggerRescore });
    const msg = triggerRescore ? '评分配置已保存并触发重算' : '评分配置已保存';
    showToast(msg, 'success');
    setTriggerRescore(false);
    await refetchScoringConfig();
  };

  const exportScoringConfig = () => {
    if (!scoringDraft) return;
    const blob = new Blob([JSON.stringify(scoringDraft, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `scoring-config-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
    showToast('评分配置已导出 JSON', 'success');
  };

  const saveProcessingConfig = async () => {
    if (!processingDraft) return;
    await apiPost('/processing/config', { config: processingDraft, active_template: activeProcessingTemplate });
    showToast('分析处理配置已保存', 'success');
    await refetchProcessingConfig();
  };

  const runProcessingBatch = async () => {
    if (!processingDraft) return;
    setRunningBatch(true);
    try {
      const payload: Record<string, any> = {
        scope_type: processingDraft.scope_type,
        force: false,
      };
      if (processingDraft.scope_type === 'recent') {
        payload.recent_days = processingDraft.scope_recent_days;
      }
      if (processingDraft.scope_type === 'tag') {
        payload.tag = processingDraft.scope_tag;
      }
      const res = await apiPost<ProcessingBatchResponse>('/processing/run_batch', payload);
      showToast(`已投递 ${res.enqueued}/${res.requested} 个钱包`, 'success');
    } catch (err: any) {
      showToast(err?.message ?? '批处理启动失败', 'error');
    } finally {
      setRunningBatch(false);
    }
  };

  const beginEditLeaderboard = (lb?: LeaderboardResponse) => {
    if (!lb) {
      setLeaderboardDraft({ ...defaultLeaderboardDraft });
      return;
    }
    setLeaderboardDraft({
      ...lb,
      filters: Array.isArray(lb.filters) ? lb.filters : [],
      filtersText: JSON.stringify(lb.filters ?? [], null, 2),
    });
  };

  const saveLeaderboard = async () => {
    if (!leaderboardDraft) return;
    let parsedFilters: any[] = [];
    if (leaderboardDraft.filtersText.trim()) {
      try {
        const parsed = JSON.parse(leaderboardDraft.filtersText);
        if (!Array.isArray(parsed)) {
          throw new Error('过滤规则必须是数组');
        }
        parsedFilters = parsed;
      } catch (err: any) {
        showToast(err?.message ?? '过滤规则必须是合法 JSON 数组', 'error');
        return;
      }
    }
    const payload = {
      name: leaderboardDraft.name,
      type: leaderboardDraft.type,
      description: leaderboardDraft.description,
      icon: leaderboardDraft.icon,
      style: leaderboardDraft.style,
      accent_color: leaderboardDraft.accent_color,
      badge: leaderboardDraft.badge,
      filters: parsedFilters,
      sort_key: leaderboardDraft.sort_key,
      sort_order: leaderboardDraft.sort_order,
      period: leaderboardDraft.period,
      is_public: leaderboardDraft.is_public,
      result_limit: leaderboardDraft.result_limit,
      auto_refresh_minutes: leaderboardDraft.auto_refresh_minutes,
    };
    setSavingLeaderboard(true);
    try {
      let resp: LeaderboardResponse;
      if (leaderboardDraft.id) {
        resp = await apiPut<LeaderboardResponse>(`/leaderboards/${leaderboardDraft.id}`, payload);
        showToast('榜单已更新', 'success');
      } else {
        resp = await apiPost<LeaderboardResponse>('/leaderboards', payload);
        showToast('榜单已创建', 'success');
      }
      setLeaderboardDraft({
        ...resp,
        filters: Array.isArray(resp.filters) ? resp.filters : [],
        filtersText: JSON.stringify(resp.filters ?? [], null, 2),
      });
      await refetchAdminLeaderboards();
    } catch (err: any) {
      showToast(err?.message ?? '保存榜单失败', 'error');
    } finally {
      setSavingLeaderboard(false);
    }
  };

  const runLeaderboard = async (id: number) => {
    try {
      await apiPost(`/leaderboards/${id}/run`);
      showToast('榜单已刷新', 'success');
    } catch (err: any) {
      showToast(err?.message ?? '刷新失败', 'error');
    }
  };

  const tabButtons = useMemo(
    () => [
      { key: 'notifications', label: '通知配置' },
      { key: 'schedules', label: '调度任务' },
      { key: 'preferences', label: '用户偏好' },
      { key: 'processing', label: '分析处理设置' },
      { key: 'scoring', label: '评分配置' },
      { key: 'leaderboards', label: '榜单配置' },
    ],
    []
  );

  return (
    <div className="page">
      <section className="card">
        <h2>后台配置中心</h2>
        <p className="muted">按模块管理通知、调度、处理与评分设置，保存后即时生效。</p>
        <div className="tab-bar">
          {tabButtons.map((tab) => (
            <button
              key={tab.key}
              className={`tab-btn ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.key as AdminTab)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </section>

      {activeTab === 'notifications' && (
        <>
          <section className="card">
            <h3>通知模板</h3>
            <p className="muted">
              模板支持变量（如 <code>{'{{wallet}}'}</code>），用于告警、任务通知等场景。
            </p>
            <div className="filters">
              <input placeholder="名称" value={newTemplate.name} onChange={(e) => setNewTemplate((p) => ({ ...p, name: e.target.value }))} />
              <select value={newTemplate.channel} onChange={(e) => setNewTemplate((p) => ({ ...p, channel: e.target.value }))}>
                <option value="email">Email</option>
                <option value="webhook">Webhook</option>
              </select>
              <input placeholder="主题" value={newTemplate.subject} onChange={(e) => setNewTemplate((p) => ({ ...p, subject: e.target.value }))} />
              <input placeholder="内容 (支持变量，如 wallet)" value={newTemplate.content} onChange={(e) => setNewTemplate((p) => ({ ...p, content: e.target.value }))} />
              <button
                className="btn primary"
                onClick={async () => {
                  await apiPost('/notifications/templates', newTemplate);
                  await refetchTemplates();
                  showToast('模板已创建', 'success');
                }}
              >
                创建模板
              </button>
            </div>
            <ul className="muted">
              {templates?.map((tpl) => (
                <li key={tpl.id}>
                  #{tpl.id} [{tpl.channel}] {tpl.name}
                </li>
              ))}
            </ul>
          </section>

          <section className="card">
            <h3>通知订阅</h3>
            <p className="muted">订阅可将模板绑定到邮箱或 Webhook，便于任务告警。</p>
            <div className="filters">
              <input placeholder="模板ID" value={newSub.template_id} onChange={(e) => setNewSub((p) => ({ ...p, template_id: e.target.value }))} />
              <input placeholder="收件人/URL" value={newSub.recipient} onChange={(e) => setNewSub((p) => ({ ...p, recipient: e.target.value }))} />
              <button
                className="btn primary"
                onClick={async () => {
                  await apiPost('/notifications/subscriptions', { template_id: Number(newSub.template_id), recipient: newSub.recipient });
                  await refetchSubs();
                  showToast('订阅已添加', 'success');
                }}
              >
                订阅
              </button>
            </div>
            <ul className="muted">
              {subs?.map((sub) => (
                <li key={sub.id}>
                  #{sub.id} 模板{sub.template_id} &gt; {sub.recipient}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}

      {activeTab === 'schedules' && (
        <section className="card">
          <h3>调度任务</h3>
          <p className="muted">为排行榜刷新、钱包同步等场景创建 Cron 调度。</p>
          <div className="filters">
            <input placeholder="名称" value={newSchedule.name} onChange={(e) => setNewSchedule((p) => ({ ...p, name: e.target.value }))} />
            <select value={newSchedule.job_type} onChange={(e) => setNewSchedule((p) => ({ ...p, job_type: e.target.value }))}>
              <option value="leaderboard_run_all">刷新榜单</option>
              <option value="wallet_sync">同步钱包</option>
            </select>
            <input placeholder="Cron" value={newSchedule.cron} onChange={(e) => setNewSchedule((p) => ({ ...p, cron: e.target.value }))} />
            {newSchedule.job_type === 'wallet_sync' && (
              <input placeholder="钱包地址" value={newSchedule.address} onChange={(e) => setNewSchedule((p) => ({ ...p, address: e.target.value }))} />
            )}
            <button
              className="btn primary"
              onClick={async () => {
                await apiPost('/schedules', {
                  name: newSchedule.name || '自动任务',
                  job_type: newSchedule.job_type,
                  cron: newSchedule.cron,
                  payload: newSchedule.job_type === 'wallet_sync' ? { address: newSchedule.address } : undefined,
                });
                await refetchSchedules();
                showToast('调度已创建', 'success');
              }}
            >
              创建调度
            </button>
          </div>
          <ul className="muted">
            {schedules?.map((job) => (
              <li key={job.id}>
                {job.name} ({job.job_type}) - {job.cron}
              </li>
            ))}
          </ul>
        </section>
      )}

      {activeTab === 'preferences' && (
        <section className="card">
          <h3>用户偏好</h3>
          <p className="muted">用于指定后台用户默认的时间周期、主题等习惯。</p>
          <div className="filters">
            <input placeholder="用户邮箱" value={email} onChange={(e) => setEmail(e.target.value)} />
            <button className="btn secondary" onClick={loadPrefs}>
              读取
            </button>
          </div>
          {prefs && (
            <div className="settings-grid">
              <label>
                默认周期
                <select value={prefs.default_period} onChange={(e) => setPrefs({ ...prefs, default_period: e.target.value })}>
                  <option value="7d">7 天</option>
                  <option value="30d">30 天</option>
                  <option value="90d">90 天</option>
                </select>
              </label>
              <label>
                默认排序
                <select value={prefs.default_sort} onChange={(e) => setPrefs({ ...prefs, default_sort: e.target.value })}>
                  <option value="score">胜率</option>
                  <option value="total_pnl">累计盈亏</option>
                </select>
              </label>
              <label>
                主题
                <select value={prefs.theme} onChange={(e) => setPrefs({ ...prefs, theme: e.target.value })}>
                  <option value="dark">暗色</option>
                  <option value="light">亮色</option>
                </select>
              </label>
              <label>
                收藏钱包
                <input value={prefs.favorite_wallets.join(',')} onChange={(e) => setPrefs({ ...prefs, favorite_wallets: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })} />
              </label>
              <label>
                收藏榜单ID
                <input
                  value={prefs.favorite_leaderboards.join(',')}
                  onChange={(e) =>
                    setPrefs({
                      ...prefs,
                      favorite_leaderboards: e.target.value
                        .split(',')
                        .map((s) => Number(s.trim()))
                        .filter((n) => !Number.isNaN(n)),
                    })
                  }
                />
              </label>
            </div>
          )}
          <button className="btn primary" onClick={savePrefs} disabled={!prefs}>
            保存偏好
          </button>
        </section>
      )}

      {activeTab === 'processing' && (
        <section className="card">
          <h3>分析处理设置</h3>
          <p className="muted">配置钱包同步、评分、AI 分析的并发与重试策略。</p>
          {!processingDraft && <p className="muted">加载中...</p>}
          {processingDraft && (
            <>
              {processingConfigResp?.templates?.length ? (
                <div className="template-grid">
                  {processingConfigResp.templates.map((tpl) => (
                    <button
                      type="button"
                      key={tpl.key}
                      className={`template-card ${activeProcessingTemplate === tpl.key ? 'active' : ''}`}
                      onClick={() => applyProcessingTemplate(tpl)}
                    >
                      <div className="template-card-header">
                        <strong>{tpl.name}</strong>
                        {activeProcessingTemplate === tpl.key && <span className="badge">当前</span>}
                      </div>
                      <p className="muted">{tpl.description}</p>
                    </button>
                  ))}
                </div>
              ) : null}
              <div className="settings-grid">
                <label>
                  同步并发数
                  <input
                    type="number"
                    value={processingDraft.max_parallel_sync}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.max_parallel_sync = Number(e.target.value)))}
                  />
                  <span className="muted">同时执行的钱包同步任务数</span>
                </label>
                <label>
                  评分并发数
                  <input
                    type="number"
                    value={processingDraft.max_parallel_score}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.max_parallel_score = Number(e.target.value)))}
                  />
                  <span className="muted">评分任务同时运行数量</span>
                </label>
                <label>
                  失败重试次数
                  <input
                    type="number"
                    value={processingDraft.retry_limit}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.retry_limit = Number(e.target.value)))}
                  />
                  <span className="muted">单阶段失败后最多尝试次数</span>
                </label>
                <label>
                  重试间隔 (秒)
                  <input
                    type="number"
                    value={processingDraft.retry_delay_seconds}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.retry_delay_seconds = Number(e.target.value)))}
                  />
                </label>
                <label>
                  评分刷新周期 (天)
                  <input
                    type="number"
                    value={processingDraft.rescore_period_days}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.rescore_period_days = Number(e.target.value)))}
                  />
                </label>
                <label>
                  触发重算阈值 (%)
                  <input
                    type="number"
                    value={processingDraft.rescore_trigger_pct}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.rescore_trigger_pct = Number(e.target.value)))}
                  />
                  <span className="muted">收益/回撤变动超过该比例时记入重算队列</span>
                </label>
                <label>
                  AI 分析周期 (天)
                  <input
                    type="number"
                    value={processingDraft.ai_period_days}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.ai_period_days = Number(e.target.value)))}
                  />
                </label>
                <label>
                  处理范围
                  <select
                    value={processingDraft.scope_type}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.scope_type = e.target.value))}
                  >
                    <option value="all">全部钱包</option>
                    <option value="today">仅今日导入</option>
                    <option value="recent">最近 N 天导入</option>
                    <option value="tag">指定标签</option>
                  </select>
                  <span className="muted">决定批处理优先关注哪些钱包</span>
                </label>
                {processingDraft.scope_type === 'recent' && (
                  <label>
                    最近天数
                    <input
                      type="number"
                      value={processingDraft.scope_recent_days}
                      onChange={(e) => updateProcessingDraft((draft) => (draft.scope_recent_days = Number(e.target.value)))}
                    />
                  </label>
                )}
                {processingDraft.scope_type === 'tag' && (
                  <label>
                    标签关键字
                    <input
                      value={processingDraft.scope_tag || ''}
                      onChange={(e) => updateProcessingDraft((draft) => (draft.scope_tag = e.target.value))}
                    />
                    <span className="muted">仅处理包含该标签的钱包</span>
                  </label>
                )}
                <label>
                  批次大小
                  <input
                    type="number"
                    value={processingDraft.batch_size}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.batch_size = Number(e.target.value)))}
                  />
                  <span className="muted">每批最多入队钱包数量</span>
                </label>
                <label>
                  批次间隔 (秒)
                  <input
                    type="number"
                    value={processingDraft.batch_interval_seconds}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.batch_interval_seconds = Number(e.target.value)))}
                  />
                  <span className="muted">定时任务两批之间的等待时间</span>
                </label>
                <label>
                  API 速率 (次/分钟)
                  <input
                    type="number"
                    value={processingDraft.request_rate_per_min}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.request_rate_per_min = Number(e.target.value)))}
                  />
                  <span className="muted">用于限流，避免 Hyperliquid 返回 429</span>
                </label>
                <label>
                  同步冷却 (天)
                  <input
                    type="number"
                    value={processingDraft.sync_cooldown_days}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.sync_cooldown_days = Number(e.target.value)))}
                  />
                </label>
                <label>
                  评分冷却 (天)
                  <input
                    type="number"
                    value={processingDraft.score_cooldown_days}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.score_cooldown_days = Number(e.target.value)))}
                  />
                </label>
                <label>
                  AI 冷却 (天)
                  <input
                    type="number"
                    value={processingDraft.ai_cooldown_days}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.ai_cooldown_days = Number(e.target.value)))}
                  />
                </label>
                <label>
                  Portfolio 刷新 (小时)
                  <input
                    type="number"
                    value={processingDraft.portfolio_refresh_hours}
                    onChange={(e) => updateProcessingDraft((draft) => (draft.portfolio_refresh_hours = Number(e.target.value)))}
                  />
                  <span className="muted">用于控制官方 Portfolio 曲线的刷新频率</span>
                </label>
              </div>
              <div className="header-actions">
                <button className="btn primary" onClick={saveProcessingConfig} disabled={!processingDraft}>
                  保存分析设置
                </button>
                <button className="btn secondary" onClick={runProcessingBatch} disabled={runningBatch}>
                  {runningBatch ? '批量提交中...' : '按当前范围立即处理'}
                </button>
              </div>
              <p className="muted">提示：批处理会按照上方的范围与批次配置，立即将一批钱包加入队列。</p>
            </>
          )}
        </section>
      )}

      {activeTab === 'scoring' && (
        <section className="card">
          <h3>评分配置</h3>
          {!scoringDraft && <p className="muted">加载中...</p>}
          {scoringDraft && (
            <>
              <div className="filters">
                <label className="checkbox-row">
                  <input type="checkbox" checked={triggerRescore} onChange={(e) => setTriggerRescore(e.target.checked)} />
                  保存后重新评分所有钱包
                </label>
                <button className="btn secondary" onClick={exportScoringConfig}>
                  导出 JSON
                </button>
              </div>
              <div className="settings-grid">
                {scoringDraft.dimensions.map((dim, idx) => (
                  <div key={dim.key} className="score-dimension">
                    <div className="dimension-header">
                      <h4>{dim.name}</h4>
                      <label>
                        权重
                        <input
                          type="number"
                          value={dim.weight}
                          onChange={(e) =>
                            updateScoringDraft((next) => {
                              next.dimensions[idx].weight = Number(e.target.value);
                            })
                          }
                        />
                      </label>
                    </div>
                    <p className="muted">{dimensionHints[dim.key] ?? ''}</p>
                    <p className="muted">指标范围 / 权重</p>
                    {dim.indicators.map((indicator, indIdx) => (
                      <div key={`${indicator.field}-${indIdx}`} className="indicator-row">
                        <div className="indicator-meta">
                          <strong>{indicator.field}</strong>
                          <span>{indicatorMeta[indicator.field] ?? ''}</span>
                        </div>
                        <div className="indicator-fields">
                          <label>
                            最小值
                            <input
                              type="number"
                              value={indicator.min}
                              onChange={(e) =>
                                updateScoringDraft((next) => {
                                  next.dimensions[idx].indicators[indIdx].min = Number(e.target.value);
                                })
                              }
                            />
                          </label>
                          <label>
                            最大值
                            <input
                              type="number"
                              value={indicator.max}
                              onChange={(e) =>
                                updateScoringDraft((next) => {
                                  next.dimensions[idx].indicators[indIdx].max = Number(e.target.value);
                                })
                              }
                            />
                          </label>
                          <label className="checkbox-row inline">
                            <input
                              type="checkbox"
                              checked={indicator.higher_is_better}
                              onChange={(e) =>
                                updateScoringDraft((next) => {
                                  next.dimensions[idx].indicators[indIdx].higher_is_better = e.target.checked;
                                })
                              }
                            />
                            越高越好
                          </label>
                          <label>
                            权重
                            <input
                              type="number"
                              value={indicator.weight}
                              onChange={(e) =>
                                updateScoringDraft((next) => {
                                  next.dimensions[idx].indicators[indIdx].weight = Number(e.target.value);
                                })
                              }
                            />
                          </label>
                        </div>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>等级</th>
                      <th>最低分</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scoringDraft.levels.map((level, idx) => (
                      <tr key={level.level}>
                        <td>{level.level}</td>
                        <td>
                          <input
                            type="number"
                            value={level.min_score}
                            onChange={(e) =>
                              updateScoringDraft((next) => {
                                next.levels[idx].min_score = Number(e.target.value);
                              })
                            }
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <button className="btn primary" onClick={saveScoringConfig}>
                保存评分配置
              </button>
            </>
          )}
        </section>
      )}

      {activeTab === 'leaderboards' && (
        <section className="card">
          <h3>榜单配置</h3>
          <p className="muted">可调整榜单的排序、规则、展示数量及自动刷新频率。</p>
          <div className="leaderboard-admin">
            <div className="leaderboard-admin-list">
              <button className="btn secondary small" onClick={() => beginEditLeaderboard(undefined)}>
                + 新建榜单
              </button>
              <div className="scrollable">
                {adminLeaderboards?.map((lb) => (
                  <div
                    key={lb.id}
                    className={`scope-card leaderboard-item ${leaderboardDraft?.id === lb.id ? 'active' : ''}`}
                    style={{ borderColor: leaderboardDraft?.id === lb.id ? lb.accent_color : 'rgba(255,255,255,0.05)' }}
                  >
                    <div className="leaderboard-item-header">
                      <div>
                        <strong>{lb.name}</strong>
                        <p className="muted">{lb.description || '暂无描述'}</p>
                      </div>
                      <span className="badge" style={{ background: lb.accent_color }}>
                        {lb.result_limit} 个
                      </span>
                    </div>
                    <p className="muted">排序：{lb.sort_key}（{lb.sort_order}）</p>
                    <p className="muted">自动刷新：{lb.auto_refresh_minutes ? `${lb.auto_refresh_minutes} 分钟` : '关闭'}</p>
                    <div className="button-row">
                      <button className="btn small" onClick={() => beginEditLeaderboard(lb)}>
                        编辑
                      </button>
                      <button className="btn small secondary" onClick={() => runLeaderboard(lb.id)}>
                        手动刷新
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="leaderboard-editor">
              {leaderboardDraft ? (
                <>
                  <div className="form-grid">
                    <div className="form-field">
                      <label>榜单名称</label>
                      <input value={leaderboardDraft.name} onChange={(e) => setLeaderboardDraft((prev) => (prev ? { ...prev, name: e.target.value } : prev))} />
                    </div>
                    <div className="form-field">
                      <label>类型</label>
                      <select value={leaderboardDraft.type} onChange={(e) => setLeaderboardDraft((prev) => (prev ? { ...prev, type: e.target.value } : prev))}>
                        <option value="custom">自定义</option>
                        <option value="preset">预设</option>
                      </select>
                    </div>
                    <div className="form-field">
                      <label>风格</label>
                      <select value={leaderboardDraft.style} onChange={(e) => setLeaderboardDraft((prev) => (prev ? { ...prev, style: e.target.value } : prev))}>
                        <option value="table">表格</option>
                        <option value="card">卡片</option>
                      </select>
                    </div>
                    <div className="form-field">
                      <label>图标/表情</label>
                      <input value={leaderboardDraft.icon ?? ''} onChange={(e) => setLeaderboardDraft((prev) => (prev ? { ...prev, icon: e.target.value } : prev))} />
                    </div>
                    <div className="form-field">
                      <label>强调色</label>
                      <input type="color" value={leaderboardDraft.accent_color} onChange={(e) => setLeaderboardDraft((prev) => (prev ? { ...prev, accent_color: e.target.value } : prev))} />
                    </div>
                    <div className="form-field">
                      <label>排序字段</label>
                      <input value={leaderboardDraft.sort_key} onChange={(e) => setLeaderboardDraft((prev) => (prev ? { ...prev, sort_key: e.target.value } : prev))} />
                    </div>
                    <div className="form-field">
                      <label>排序方向</label>
                      <select value={leaderboardDraft.sort_order} onChange={(e) => setLeaderboardDraft((prev) => (prev ? { ...prev, sort_order: e.target.value } : prev))}>
                        <option value="desc">降序</option>
                        <option value="asc">升序</option>
                      </select>
                    </div>
                    <div className="form-field">
                      <label>周期</label>
                      <select value={leaderboardDraft.period} onChange={(e) => setLeaderboardDraft((prev) => (prev ? { ...prev, period: e.target.value } : prev))}>
                        <option value="day">日</option>
                        <option value="week">周</option>
                        <option value="month">月</option>
                        <option value="all">全部</option>
                      </select>
                    </div>
                    <div className="form-field">
                      <label>展示数量</label>
                      <input
                        type="number"
                        min={1}
                        max={200}
                        value={leaderboardDraft.result_limit}
                        onChange={(e) => setLeaderboardDraft((prev) => (prev ? { ...prev, result_limit: Number(e.target.value) } : prev))}
                      />
                    </div>
                    <div className="form-field">
                      <label>自动刷新（分钟）</label>
                      <input
                        type="number"
                        min={0}
                        value={leaderboardDraft.auto_refresh_minutes}
                        onChange={(e) =>
                          setLeaderboardDraft((prev) => (prev ? { ...prev, auto_refresh_minutes: Number(e.target.value) } : prev))
                        }
                      />
                    </div>
                    <div className="form-field">
                      <label>公开展示</label>
                      <div className="checkbox-row inline">
                        <input
                          type="checkbox"
                          checked={leaderboardDraft.is_public}
                          onChange={(e) => setLeaderboardDraft((prev) => (prev ? { ...prev, is_public: e.target.checked } : prev))}
                        />
                        <span className="muted">对前台可见</span>
                      </div>
                    </div>
                  </div>
                  <div className="form-field">
                    <label>描述</label>
                    <textarea
                      className="note-editor"
                      value={leaderboardDraft.description ?? ''}
                      onChange={(e) => setLeaderboardDraft((prev) => (prev ? { ...prev, description: e.target.value } : prev))}
                    />
                  </div>
                  <div className="form-field">
                    <label>过滤规则（JSON 数组）</label>
                    <textarea
                      className="json-input"
                      value={leaderboardDraft.filtersText}
                      onChange={(e) => setLeaderboardDraft((prev) => (prev ? { ...prev, filtersText: e.target.value } : prev))}
                    />
                    <p className="indicator-hint">
                      示例：{`[{"source":"metric","field":"win_rate","op":">=","value":0.6}]`}
                    </p>
                  </div>
                  <div className="button-row">
                    <button className="btn primary" onClick={saveLeaderboard} disabled={savingLeaderboard}>
                      {savingLeaderboard ? '保存中...' : '保存榜单'}
                    </button>
                  </div>
                </>
              ) : (
                <p className="muted">请选择左侧榜单或点击“新建榜单”。</p>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
