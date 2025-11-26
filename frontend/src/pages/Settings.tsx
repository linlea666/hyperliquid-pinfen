import { useState } from 'react';
import { apiGet, apiPost } from '../api/client';
import type { PreferenceResponse } from '../types';
import { showToast } from '../utils/toast';

export default function Settings() {
  const [email, setEmail] = useState(() => (typeof window !== 'undefined' ? localStorage.getItem('userEmail') ?? '' : ''));
  const [prefs, setPrefs] = useState<PreferenceResponse | null>(null);
  const [activeTab, setActiveTab] = useState<'prefs' | 'cache'>('prefs');

  const loadPreferences = async () => {
    if (!email) {
      showToast('请先填写邮箱', 'error');
      return;
    }
    const data = await apiGet<PreferenceResponse>(`/admin/preferences?email=${encodeURIComponent(email)}`);
    setPrefs(data);
    if (typeof window !== 'undefined') {
      localStorage.setItem('userPreferences', JSON.stringify(data));
      localStorage.setItem('userEmail', email);
    }
    showToast('偏好已加载并缓存到本地', 'success');
  };

  const savePreferences = async () => {
    if (!email || !prefs) {
      showToast('请先加载偏好配置', 'error');
      return;
    }
    const payload = { ...prefs };
    await apiPost(`/admin/preferences?email=${encodeURIComponent(email)}`, payload);
    localStorage.setItem('userPreferences', JSON.stringify(payload));
    localStorage.setItem('userEmail', email);
    showToast('偏好已保存', 'success');
  };

  return (
    <div className="page">
      <section className="card">
        <h2>设置中心</h2>
        <p className="muted">管理后台用户的展示偏好以及本地缓存。</p>
        <div className="tab-bar">
          <button className={`tab-btn ${activeTab === 'prefs' ? 'active' : ''}`} onClick={() => setActiveTab('prefs')}>
            用户偏好
          </button>
          <button className={`tab-btn ${activeTab === 'cache' ? 'active' : ''}`} onClick={() => setActiveTab('cache')}>
            本地缓存
          </button>
        </div>
      </section>

      {activeTab === 'prefs' && (
        <section className="card">
          <h3>用户偏好配置</h3>
          <div className="filters">
            <input placeholder="用户邮箱" value={email} onChange={(e) => setEmail(e.target.value)} />
            <button className="btn secondary" onClick={loadPreferences}>
              加载偏好
            </button>
          </div>
          {prefs ? (
            <>
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
              <button className="btn primary" onClick={savePreferences}>
                保存偏好
              </button>
            </>
          ) : (
            <p className="muted">填写邮箱并点击“加载偏好”后即可编辑默认展示方式。</p>
          )}
        </section>
      )}

      {activeTab === 'cache' && (
        <section className="card">
          <h3>本地缓存管理</h3>
          <p className="muted">当浏览器缓存配置与服务器不同步时，可一键清除重新加载。</p>
          <button
            className="btn secondary"
            onClick={() => {
              if (typeof window !== 'undefined') {
                localStorage.removeItem('userPreferences');
                localStorage.removeItem('userEmail');
                showToast('本地缓存已清除', 'success');
              }
            }}
          >
            清除本地偏好缓存
          </button>
        </section>
      )}
    </div>
  );
}
