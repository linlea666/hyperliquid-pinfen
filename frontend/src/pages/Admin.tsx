import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api/client';
import type {
  Schedule,
  TemplateResponse,
  SubscriptionResponse,
  PreferenceResponse,
  ScoringConfigResponse,
  ScoringConfig,
  ProcessingConfigResponse,
  ProcessingConfig,
} from '../types';

export default function AdminPanel() {
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');

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

  useEffect(() => {
    if (scoringConfigResp) {
      setScoringDraft(JSON.parse(JSON.stringify(scoringConfigResp.config)));
    }
  }, [scoringConfigResp]);

  useEffect(() => {
    if (processingConfigResp) {
      setProcessingDraft(JSON.parse(JSON.stringify(processingConfigResp.config)));
    }
  }, [processingConfigResp]);

  const loadPrefs = async () => {
    if (!email) return;
    const data = await apiGet<PreferenceResponse>(`/admin/preferences?email=${encodeURIComponent(email)}`);
    setPrefs(data);
    setMessage('已加载用户偏好');
  };

  const savePrefs = async () => {
    if (!email || !prefs) return;
    await apiPost(`/admin/preferences?email=${encodeURIComponent(email)}`, prefs);
    setMessage('用户偏好已保存');
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

  const saveScoringConfig = async () => {
    if (!scoringDraft) return;
    await apiPost('/scoring/config', { config: scoringDraft, trigger_rescore: triggerRescore });
    setMessage(triggerRescore ? '评分配置已保存并触发重算' : '评分配置已保存');
    setTriggerRescore(false);
    await refetchScoringConfig();
  };

  const saveProcessingConfig = async () => {
    if (!processingDraft) return;
    await apiPost('/processing/config', { config: processingDraft });
    setMessage('分析处理配置已保存');
    await refetchProcessingConfig();
  };

  return (
    <div className="page">
      <section className="card">
        <h2>管理员设置</h2>
        <p className="muted">已通过账号登录，所有配置均需权限。</p>
      </section>

      <section className="card">
        <h3>通知模板</h3>
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
        <div className="filters">
          <input placeholder="模板ID" value={newSub.template_id} onChange={(e) => setNewSub((p) => ({ ...p, template_id: e.target.value }))} />
          <input placeholder="收件人/URL" value={newSub.recipient} onChange={(e) => setNewSub((p) => ({ ...p, recipient: e.target.value }))} />
          <button
            className="btn primary"
            onClick={async () => {
              await apiPost('/notifications/subscriptions', { template_id: Number(newSub.template_id), recipient: newSub.recipient });
              await refetchSubs();
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

      <section className="card">
        <h3>调度任务</h3>
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

      <section className="card">
        <h3>用户偏好</h3>
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

      <section className="card">
        <h3>分析处理设置</h3>
        {!processingDraft && <p className="muted">加载中...</p>}
        {processingDraft && (
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
          </div>
        )}
        <button className="btn primary" onClick={saveProcessingConfig} disabled={!processingDraft}>
          保存分析设置
        </button>
      </section>

      <section className="card">
        <h3>评分配置</h3>
        {!scoringDraft && <p className="muted">加载中...</p>}
        {scoringDraft && (
          <>
            <div className="filters">
              <label>
                <input type="checkbox" checked={triggerRescore} onChange={(e) => setTriggerRescore(e.target.checked)} />
                保存后重新评分所有钱包
              </label>
            </div>
            <div className="settings-grid">
              {scoringDraft.dimensions.map((dim, idx) => (
                <div key={dim.key} className="card" style={{ background: 'rgba(255,255,255,0.02)' }}>
                  <h4>{dim.name}</h4>
                  <label>
                    权重
                    <input
                      type="number"
                      value={dim.weight}
                      onChange={(e) => updateScoringDraft((next) => {
                        next.dimensions[idx].weight = Number(e.target.value);
                      })}
                    />
                  </label>
                  <p className="muted">指标</p>
                  {dim.indicators.map((indicator, indIdx) => (
                    <div key={`${indicator.field}-${indIdx}`} className="indicator-grid">
                      <span>{indicator.field}</span>
                      <input
                        type="number"
                        value={indicator.min}
                        onChange={(e) => updateScoringDraft((next) => {
                          next.dimensions[idx].indicators[indIdx].min = Number(e.target.value);
                        })}
                      />
                      <input
                        type="number"
                        value={indicator.max}
                        onChange={(e) => updateScoringDraft((next) => {
                          next.dimensions[idx].indicators[indIdx].max = Number(e.target.value);
                        })}
                      />
                      <label className="checkbox-row">
                        <input
                          type="checkbox"
                          checked={indicator.higher_is_better}
                          onChange={(e) => updateScoringDraft((next) => {
                            next.dimensions[idx].indicators[indIdx].higher_is_better = e.target.checked;
                          })}
                        />
                        越高越好
                      </label>
                      <input
                        type="number"
                        value={indicator.weight}
                        onChange={(e) => updateScoringDraft((next) => {
                          next.dimensions[idx].indicators[indIdx].weight = Number(e.target.value);
                        })}
                      />
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
                      onChange={(e) => updateScoringDraft((next) => {
                        next.levels[idx].min_score = Number(e.target.value);
                      })}
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

      {message && <p className="muted">{message}</p>}
    </div>
  );
}
