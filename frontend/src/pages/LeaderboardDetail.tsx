import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate, useParams } from 'react-router-dom';

import { apiGet } from '../api/client';
import type { LeaderboardResultResponse } from '../types';

export default function LeaderboardDetail() {
  const navigate = useNavigate();
  const { id } = useParams();
  const numericId = useMemo(() => {
    if (!id) return null;
    const parsed = Number(id);
    return Number.isNaN(parsed) ? null : parsed;
  }, [id]);
  const [sortKey, setSortKey] = useState<'rank' | 'win_rate' | 'total_pnl' | 'return_7d' | 'return_30d'>('rank');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const { data, isLoading, error } = useQuery<LeaderboardResultResponse>({
    queryKey: ['leaderboard-detail-page', numericId],
    queryFn: () => apiGet<LeaderboardResultResponse>(`/leaderboards/${numericId}`),
    enabled: numericId !== null,
  });

  const copyLink = async () => {
    if (typeof window === 'undefined') return;
    try {
      await navigator.clipboard.writeText(window.location.href);
      alert('链接已复制');
    } catch (err) {
      console.warn('Copy failed', err);
    }
  };

  if (!numericId) {
    return (
      <div className="page">
        <section className="card">
          <p className="muted">无效的榜单编号。</p>
        </section>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="page">
        <section className="card">加载中...</section>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="page">
        <section className="card error">加载失败：{(error as Error)?.message ?? '未知错误'}</section>
      </div>
    );
  }

  const lb = data.leaderboard;

  const formatWinRate = (val?: number | string) => {
    if (val === undefined || val === null) return '--';
    const num = Number(val);
    if (Number.isNaN(num)) return '--';
    return `${(num * 100).toFixed(1)}%`;
  };

  const formatReturn = (entry: LeaderboardResultResponse['results'][number], key: string) => {
    const value = entry.metrics?.periods?.[key]?.return;
    if (value === undefined || value === null) return '--';
    const num = Number(value);
    return `${num >= 0 ? '+' : ''}${num.toFixed(2)}%`;
  };

  const formatCurrency = (value?: number | string) => {
    if (value === undefined || value === null) return '--';
    const num = Number(value);
    if (Number.isNaN(num)) return '--';
    return num >= 1000 ? num.toLocaleString(undefined, { maximumFractionDigits: 0 }) : num.toFixed(2);
  };

  const sortedResults = useMemo(() => {
    if (!data) return [];
    const clone = [...data.results];
    switch (sortKey) {
      case 'win_rate':
        clone.sort((a, b) => (Number(b.metrics?.win_rate ?? 0) - Number(a.metrics?.win_rate ?? 0)));
        break;
      case 'total_pnl':
        clone.sort((a, b) => Number(b.metrics?.total_pnl ?? 0) - Number(a.metrics?.total_pnl ?? 0));
        break;
      case 'return_7d':
        clone.sort(
          (a, b) => Number(b.metrics?.periods?.['7d']?.return ?? 0) - Number(a.metrics?.periods?.['7d']?.return ?? 0),
        );
        break;
      case 'return_30d':
        clone.sort(
          (a, b) => Number(b.metrics?.periods?.['30d']?.return ?? 0) - Number(a.metrics?.periods?.['30d']?.return ?? 0),
        );
        break;
      default:
        clone.sort((a, b) => a.rank - b.rank);
    }
    return clone;
  }, [data, sortKey]);

  const totalPages = Math.max(1, Math.ceil(sortedResults.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const paginatedResults = sortedResults.slice((safePage - 1) * pageSize, safePage * pageSize);

  const exportCsv = () => {
    if (!data) return;
    const headers = ['rank', 'wallet', 'win_rate', 'total_pnl', 'return_7d', 'return_30d', 'all_pnl'];
    const rows = data.results.map((entry) => [
      entry.rank,
      entry.wallet_address,
      entry.metrics?.win_rate ?? '',
      entry.metrics?.total_pnl ?? '',
      entry.metrics?.periods?.['7d']?.return ?? '',
      entry.metrics?.periods?.['30d']?.return ?? '',
      entry.metrics?.periods?.all?.pnl ?? '',
    ]);
    const csv = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${lb.name}-leaderboard.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="page">
      <section className="card">
        <div className="leaderboard-detail-header">
          <div>
            <button className="btn secondary small" onClick={() => navigate(-1)}>
              返回
            </button>
            <h2>
              {lb.icon && <span className="emoji">{lb.icon}</span>} {lb.name}
            </h2>
            <p className="muted">{lb.description || '暂无描述'}</p>
            <p className="muted">
              排序：{lb.sort_key}（{lb.sort_order}） ｜ 周期：{lb.period} ｜ 展示数量：{lb.result_limit}
            </p>
            <p className="muted">自动刷新：{lb.auto_refresh_minutes ? `${lb.auto_refresh_minutes} 分钟` : '未启用'}</p>
          </div>
          <div className="button-row">
            <button className="btn secondary" onClick={copyLink}>
              复制链接
            </button>
            <button className="btn primary" onClick={() => window.print()}>
              导出/打印
            </button>
            <button className="btn secondary" onClick={exportCsv}>
              导出 CSV
            </button>
          </div>
        </div>
        {Array.isArray(lb.filters) && lb.filters.length > 0 && (
          <div className="filter-badges">
            {lb.filters.map((f: any, idx: number) => (
              <span key={idx} className="badge">
                {(f.source === 'portfolio' ? `官方-${f.period || 'month'}` : '指标') + ' ' + (f.field || '')} {f.op || '>='} {f.value}
              </span>
            ))}
          </div>
        )}
      </section>

      <section className="card">
        <h3>榜单结果</h3>
        <div className="table-controls">
          <label>
            排序
            <select value={sortKey} onChange={(e) => setSortKey(e.target.value as any)}>
              <option value="rank">排行顺序</option>
              <option value="win_rate">胜率（高到低）</option>
              <option value="total_pnl">累计盈亏（高到低）</option>
              <option value="return_7d">7 日收益率</option>
              <option value="return_30d">30 日收益率</option>
            </select>
          </label>
          <label>
            每页数量
            <select
              value={pageSize}
              onChange={(e) => {
                setPage(1);
                setPageSize(Number(e.target.value));
              }}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </label>
          <div className="pagination">
            <button className="btn secondary small" disabled={safePage <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
              上一页
            </button>
            <span className="muted">
              第 {safePage}/{totalPages} 页
            </span>
            <button
              className="btn secondary small"
              disabled={safePage >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              下一页
            </button>
          </div>
        </div>
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
              {paginatedResults.map((entry) => (
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
      </section>
    </div>
  );
}
