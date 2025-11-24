import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiGet } from '../api/client';
import type { WalletListResponse, WalletSummary } from '../types';

const PAGE_SIZE = 20;
const PERIOD_OPTIONS = [
  { label: '近1天', value: '1d' },
  { label: '近30天', value: '30d' },
  { label: '近1年', value: '365d' },
  { label: '全部', value: 'all' },
];
const SORT_FIELDS = [
  { label: '胜率', value: 'win_rate' },
  { label: '收益率', value: 'avg_pnl' },
  { label: '收益额', value: 'total_pnl' },
  { label: '交易次数', value: 'trades' },
];

export default function WalletList() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(0);
  const [period, setPeriod] = useState('30d');
  const [sortField, setSortField] = useState('win_rate');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [copied, setCopied] = useState('');
  const navigate = useNavigate();

  const { data, isFetching, error } = useQuery<WalletListResponse>({
    queryKey: ['wallets', { search, status, page, period, sortField, sortOrder }],
    queryFn: () =>
      apiGet<WalletListResponse>('/wallets', {
        search: search || undefined,
        status: status || undefined,
        period,
        sort_key: sortField,
        sort_order: sortOrder,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  const wallets: WalletSummary[] = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = total ? Math.ceil(total / PAGE_SIZE) : 1;

  const handleCopy = async (address: string) => {
    try {
      await navigator.clipboard.writeText(address);
      setCopied(address);
      setTimeout(() => {
        setCopied('');
      }, 2000);
    } catch {
      setCopied('');
    }
  };

  return (
    <div className="page">
      <section className="card">
        <div className="header-actions">
          <button className="btn primary" onClick={() => navigate('/wallets/import')}>
            批量导入
          </button>
        </div>
        <div className="filters stacked">
          <div className="filter-row">
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
              {SORT_FIELDS.map((field) => (
                <option key={field.value} value={field.value}>
                  {field.label}排序
                </option>
              ))}
            </select>
            <button className="btn small" onClick={() => setSortOrder((prev) => (prev === 'desc' ? 'asc' : 'desc'))}>
              {sortOrder === 'desc' ? '降序' : '升序'}
            </button>
          </div>
          <div className="period-toggle">
            {PERIOD_OPTIONS.map((option) => (
              <button
                key={option.value}
                className={`btn small ${period === option.value ? 'primary' : 'ghost'}`}
                onClick={() => {
                  setPeriod(option.value);
                  setPage(0);
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
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
              {wallets.map((wallet) => (
                <tr key={wallet.address}>
                  <td>
                    <div className="address-cell">
                      <span>{wallet.address}</span>
                      <button className="btn ghost small" onClick={() => handleCopy(wallet.address)}>
                        {copied === wallet.address ? '已复制' : '复制'}
                      </button>
                    </div>
                  </td>
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
                  <td>{wallet.metric?.win_rate ?? '--'}</td>
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
