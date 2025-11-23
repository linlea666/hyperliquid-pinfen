import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api/client';
import type { Schedule, TemplateResponse, SubscriptionResponse, PreferenceResponse } from '../types';

export default function AdminPanel() {
  const queryClient = useQueryClient();
  const [token, setToken] = useState(() => (typeof window !== 'undefined' ? localStorage.getItem('adminToken') ?? '' : ''));
  const [email, setEmail] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('adminToken', token);
    }
  }, [token]);

  const { data: templates, refetch: refetchTemplates } = useQuery<TemplateResponse[]>({
    queryKey: ['admin-templates', token],
    queryFn: () => apiGet<TemplateResponse[]>('/notifications/templates'),
    enabled: Boolean(token),
  });

  const { data: subs, refetch: refetchSubs } = useQuery<SubscriptionResponse[]>({
    queryKey: ['admin-subs', token],
    queryFn: () => apiGet<SubscriptionResponse[]>('/notifications/subscriptions'),
    enabled: Boolean(token),
  });

  const { data: schedules, refetch: refetchSchedules } = useQuery<Schedule[]>({
    queryKey: ['admin-schedules', token],
    queryFn: () => apiGet<Schedule[]>('/schedules'),
    enabled: Boolean(token),
  });

  const [newTemplate, setNewTemplate] = useState({ name: '', channel: 'email', subject: '', content: '' });
  const [newSub, setNewSub] = useState({ template_id: '', recipient: '' });
  const [newSchedule, setNewSchedule] = useState({ name: '', job_type: 'leaderboard_run_all', cron: '0 * * * *', address: '' });
  const [prefs, setPrefs] = useState<PreferenceResponse | null>(null);

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

  return (
    <div className="page">
      <section className="card">
        <h2>管理员设置</h2>
        <div className="filters">
          <input placeholder="管理员 Token" value={token} onChange={(e) => setToken(e.target.value)} />
          <button className="btn primary" onClick={() => queryClient.invalidateQueries()}>
            使用 Token
          </button>
        </div>
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

      {message && <p className="muted">{message}</p>}
    </div>
  );
}
