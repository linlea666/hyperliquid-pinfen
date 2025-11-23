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

      {selected && detail && detail.leaderboard.style === 'card' && (
        <section className="card">
          <h3>{detail.leaderboard.name} - 当前结果</h3>
          <div className="leaderboard-cards-grid">
            {detail.results.map((entry) => (
              <div key={entry.wallet_address} className="metric-card" style={{ borderColor: detail.leaderboard.accent_color }}>
                <p className="metric-title">#{entry.rank}</p>
                <p className="metric-value">{entry.wallet_address}</p>
                <p className="metric-desc">得分：{entry.score ?? '--'}</p>
              </div>
            ))}
          </div>
        </section>
      )}

      {selected && detail && detail.leaderboard.style !== 'card' && (
        <section className="card">
          <h3>{detail.leaderboard.name} - 当前结果</h3>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>排名</th>
                  <th>钱包</th>
                  <th>得分</th>
                  <th>指标</th>
                </tr>
              </thead>
              <tbody>
                {detail.results.map((entry) => (
                  <tr key={entry.wallet_address}>
                    <td>{entry.rank}</td>
                    <td>{entry.wallet_address}</td>
                    <td>{entry.score ?? '--'}</td>
                    <td>
                      {entry.metrics ? JSON.stringify(entry.metrics) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
