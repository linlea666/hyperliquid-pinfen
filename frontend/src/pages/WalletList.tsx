import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiGet } from '../api/client';
import type { WalletListResponse, WalletSummary } from '../types';

const PAGE_SIZE = 20;

export default function WalletList() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(0);
  const navigate = useNavigate();

  const { data, isFetching, error } = useQuery<WalletListResponse>({
    queryKey: ['wallets', { search, status, page }],
    queryFn: () =>
      apiGet<WalletListResponse>('/wallets', {
        search: search || undefined,
        status: status || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  const wallets: WalletSummary[] = data?.items ?? [];
  const preferences = useMemo(() => {
    if (typeof window === 'undefined') return null;
    const raw = window.localStorage.getItem('userPreferences');
    return raw ? JSON.parse(raw) : null;
  }, []);
  const favoriteWallets = preferences?.favorite_wallets ?? [];
  const [sortField, setSortField] = useState<string>(preferences?.default_sort ?? 'score');

  const sortedWallets = useMemo(() => {
    if (!wallets) return [];
    return [...wallets].sort((a, b) => {
      if (sortField === 'total_pnl') {
        return Number(b.metric?.total_pnl ?? 0) - Number(a.metric?.total_pnl ?? 0);
      }
      return Number(b.metric?.win_rate ?? 0) - Number(a.metric?.win_rate ?? 0);
    });
  }, [wallets, sortField]);

  const total = data?.total ?? 0;
  const totalPages = total ? Math.ceil(total / PAGE_SIZE) : 1;

  return (
    <div className="page">
      <section className="card">
        <div className="header-actions">
          <button className="btn primary" onClick={() => navigate('/wallets/import')}>
            批量导入
          </button>
        </div>
        <div className="filters">
          <input
            placeholder="搜索地址"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
          />
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(0);
            }}
          >
            <option value="">全部状态</option>
            <option value="imported">已导入</option>
            <option value="synced">已同步</option>
          </select>
          <select value={sortField} onChange={(e) => setSortField(e.target.value)}>
            <option value="score">胜率排序</option>
            <option value="total_pnl">累计盈亏排序</option>
          </select>
        </div>

        {isFetching && <p className="muted">加载中...</p>}
        {error && <p className="error">加载失败：{(error as Error).message}</p>}

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>地址</th>
                <th>状态</th>
                <th>标签</th>
                <th>胜率</th>
                <th>累计盈亏</th>
                <th>平均盈亏</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {sortedWallets.map((wallet) => (
                <tr key={wallet.address}>
                  <td>{wallet.address}</td>
                  <td>
                    <span className={`status ${wallet.status}`}>{wallet.status}</span>
                  </td>
                  <td>
                    {wallet.tags.length > 0 ? (
                      wallet.tags.map((tag: any) => (
                        <span
                          key={tag.id ?? tag}
                          className="tag-chip"
                          style={{ background: tag.color || 'rgba(255,255,255,0.1)' }}
                        >
                          {tag.name ?? tag}
                        </span>
                      ))
                    ) : (
                      <span className="muted">-</span>
                    )}
                  </td>
                  <td>
                    {wallet.metric?.win_rate ?? '--'}
                    {favoriteWallets.includes(wallet.address) && <span className="badge favorite">★</span>}
                  </td>
                  <td>{wallet.metric?.total_pnl ?? '--'}</td>
                  <td>{wallet.metric?.avg_pnl ?? '--'}</td>
                  <td>
                    <button className="btn small" onClick={() => navigate(`/wallets/${wallet.address}`)}>
                      查看
                    </button>
                  </td>
                </tr>
              ))}
              {!wallets.length && (
                <tr>
                  <td colSpan={7} className="muted">
                    暂无数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="pagination">
          <button
            className="btn small"
            onClick={() => setPage((p) => Math.max(p - 1, 0))}
            disabled={page === 0}
          >
            上一页
          </button>
          <span>
            第 {page + 1} / {totalPages} 页
          </span>
          <button
            className="btn small"
            onClick={() => setPage((p) => ((p + 1) < totalPages ? p + 1 : p))}
            disabled={page + 1 >= totalPages}
          >
            下一页
          </button>
        </div>
      </section>
    </div>
  );
}
