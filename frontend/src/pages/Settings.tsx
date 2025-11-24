import { useState } from 'react';
import { apiGet, apiPost } from '../api/client';
import type { PreferenceResponse } from '../types';

export default function Settings() {
  const [email, setEmail] = useState(() => (typeof window !== 'undefined' ? localStorage.getItem('userEmail') ?? '' : ''));
  const [prefs, setPrefs] = useState<PreferenceResponse | null>(null);
  const [message, setMessage] = useState('');

  const loadPreferences = async () => {
    if (!email) return;
    const data = await apiGet<PreferenceResponse>(`/admin/preferences?email=${encodeURIComponent(email)}`);
    setPrefs(data);
    if (typeof window !== 'undefined') {
      localStorage.setItem('userPreferences', JSON.stringify(data));
      localStorage.setItem('userEmail', email);
    }
    setMessage('偏好已加载并缓存到本地。');
  };

  const savePreferences = async () => {
    if (!email || !prefs) return;
    const payload = { ...prefs };
    await apiPost(`/admin/preferences?email=${encodeURIComponent(email)}`, payload);
    localStorage.setItem('userPreferences', JSON.stringify(payload));
    localStorage.setItem('userEmail', email);
    setMessage('偏好已保存。');
  };

  return (
    <div className="page">
      <section className="card">
        <h2>用户偏好配置</h2>
        <div className="filters">
          <input placeholder="用户邮箱" value={email} onChange={(e) => setEmail(e.target.value)} />
          <button className="btn primary" onClick={loadPreferences}>
            加载偏好
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
              收藏钱包（逗号分隔）
              <input
                value={prefs.favorite_wallets.join(',')}
                onChange={(e) =>
                  setPrefs({ ...prefs, favorite_wallets: e.target.value.split(',').map((s) => s.trim()).filter(Boolean) })
                }
              />
            </label>
            <label>
              收藏榜单ID（逗号分隔）
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
        <button className="btn primary" onClick={savePreferences} disabled={!prefs}>
          保存偏好
        </button>
        {message && <p className="muted">{message}</p>}
      </section>
    </div>
  );
}
