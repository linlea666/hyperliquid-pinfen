import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '../api/client';
import type { LeaderboardResponse, LeaderboardResultResponse } from '../types';

export default function Leaderboards() {
  const [selected, setSelected] = useState<number | null>(null);
  const preferences = useMemo(() => {
    if (typeof window === 'undefined') return null;
    const raw = window.localStorage.getItem('userPreferences');
    return raw ? JSON.parse(raw) : null;
  }, []);
  const favoriteLeaderboards: number[] = preferences?.favorite_leaderboards ?? [];

  const { data: leaderboards, isLoading, error } = useQuery<LeaderboardResponse[]>({
    queryKey: ['leaderboards'],
    queryFn: () => apiGet<LeaderboardResponse[]>('/leaderboards'),
  });

  const { data: detail } = useQuery<LeaderboardResultResponse>({
    queryKey: ['leaderboard-detail', selected],
    queryFn: () => apiGet<LeaderboardResultResponse>(`/leaderboards/${selected}`),
    enabled: selected != null,
  });

  useEffect(() => {
    if (!selected && leaderboards?.length) {
      setSelected(leaderboards[0].id);
    }
  }, [leaderboards, selected]);

  const formatReturn = (entry: LeaderboardResultResponse['results'][number], key: string) => {
    const value = entry.metrics?.periods?.[key]?.return;
    if (value === undefined || value === null) return '--';
    const num = Number(value);
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
  };

  const formatWinRate = (val?: number | string) => {
    if (val === undefined || val === null) return '--';
    const num = Number(val);
    if (Number.isNaN(num)) return '--';
    return `${(num * 100).toFixed(1)}%`;
  };

  const formatCurrency = (value?: number | string) => {
    if (value === undefined || value === null) return '--';
    const num = Number(value);
    if (Number.isNaN(num)) return '--';
    return num >= 1000 ? num.toLocaleString(undefined, { maximumFractionDigits: 0 }) : num.toFixed(2);
  };

  if (isLoading) {
    return <div className="card">加载中...</div>;
  }
  if (error) {
    return <div className="card error">{(error as Error).message}</div>;
  }

  return (
    <div className="page">
      <section className="card">
        <h2>榜单列表</h2>
        <div className="leaderboard-list">
          {leaderboards?.map((lb) => (
            <button
              key={lb.id}
              className={`leaderboard-card ${selected === lb.id ? 'active' : ''} ${
                favoriteLeaderboards.includes(lb.id) ? 'favorite' : ''
              }`}
              style={{ borderColor: selected === lb.id ? lb.accent_color : 'transparent' }}
              onClick={() => setSelected(lb.id)}
            >
              <h3>
                {lb.icon && <span className="emoji">{lb.icon}</span>}
                {lb.name}
                {lb.badge && <span className="badge" style={{ background: lb.accent_color }}>{lb.badge}</span>}
              </h3>
              <p className="muted">{lb.description || '暂无描述'}</p>
              <p className="muted">排序：{lb.sort_key} ({lb.sort_order})</p>
            </button>
          ))}
        </div>
      </section>

      {selected && detail && (
        <section className="card">
          <div className="leaderboard-detail-header">
            <div>
              <h3>
                {detail.leaderboard.icon && <span className="emoji">{detail.leaderboard.icon}</span>}
                {detail.leaderboard.name}
              </h3>
              <p className="muted">{detail.leaderboard.description || '暂无描述'}</p>
              <p className="muted">
                排序：{detail.leaderboard.sort_key}（{detail.leaderboard.sort_order}） ｜ 周期：{detail.leaderboard.period}
              </p>
            </div>
            <div className="leaderboard-meta">
              <p>展示数量：{detail.results.length}</p>
              <p>风格：{detail.leaderboard.style === 'card' ? '卡片' : '表格'}</p>
            </div>
          </div>
          {Array.isArray(detail.leaderboard.filters) && detail.leaderboard.filters.length > 0 && (
            <div className="filter-badges">
              {detail.leaderboard.filters.map((f: any, idx: number) => (
                <span key={idx} className="badge">
                  {(f.source === 'portfolio' ? `官方-${f.period || 'month'}` : '指标') + ' ' + (f.field || '')} {f.op || '>='} {f.value}
                </span>
              ))}
            </div>
          )}
          {detail.leaderboard.style === 'card' ? (
            <div className="leaderboard-cards-grid">
              {detail.results.map((entry) => (
                <div key={entry.wallet_address} className="metric-card" style={{ borderColor: detail.leaderboard.accent_color }}>
                  <p className="metric-title">#{entry.rank}</p>
                  <p className="metric-value">{entry.wallet_address}</p>
                  <p className="metric-desc">胜率：{formatWinRate(entry.metrics?.win_rate)}</p>
                  <p className="metric-desc">总盈亏：{formatCurrency(entry.metrics?.total_pnl)}</p>
                  <p className="metric-desc">7日收益率：{formatReturn(entry, '7d')}</p>
                  <p className="metric-desc">30日收益率：{formatReturn(entry, '30d')}</p>
                </div>
              ))}
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>排名</th>
                    <th>钱包</th>
                    <th>胜率</th>
                    <th>总盈亏</th>
                    <th>7日收益率</th>
                    <th>30日收益率</th>
                    <th>累计收益</th>
                  </tr>
                </thead>
                <tbody>
                  {detail.results.map((entry) => (
                    <tr key={entry.wallet_address}>
                      <td>{entry.rank}</td>
                      <td>{entry.wallet_address}</td>
                      <td>{formatWinRate(entry.metrics?.win_rate)}</td>
                      <td>{formatCurrency(entry.metrics?.total_pnl)}</td>
                      <td>{formatReturn(entry, '7d')}</td>
                      <td>{formatReturn(entry, '30d')}</td>
                      <td>
                        {entry.metrics?.periods?.all?.pnl
                          ? Number(entry.metrics.periods.all.pnl).toLocaleString(undefined, { maximumFractionDigits: 2 })
                          : '--'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
