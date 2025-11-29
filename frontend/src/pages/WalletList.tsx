import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiGet } from '../api/client';
import type { TagResponse, WalletListResponse, WalletSummary } from '../types';

const PAGE_SIZE = 20;
const PERIOD_OPTIONS = [
  { label: '近1天', value: '1d' },
  { label: '近30天', value: '30d' },
  { label: '近1年', value: '365d' },
  { label: '全部', value: 'all' },
];
const METRIC_SORT_FIELDS = [
  { label: '胜率', value: 'win_rate' },
  { label: '收益额', value: 'total_pnl' },
  { label: '平均收益', value: 'avg_pnl' },
  { label: '交易次数', value: 'trades' },
];

const PORTFOLIO_SORT_FIELDS = [
  { label: '官方7日收益率', value: 'portfolio_week_return' },
  { label: '官方30日收益率', value: 'portfolio_month_return' },
  { label: '官方30日回撤', value: 'portfolio_month_drawdown' },
];

const AI_SORT_FIELDS = [
  { label: 'AI得分', value: 'ai_score' },
  { label: 'AI推荐比例', value: 'ai_follow_ratio' },
];

export default function WalletList() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(0);
  const [period, setPeriod] = useState('30d');
  const [sortMode, setSortMode] = useState<'metric' | 'portfolio' | 'ai'>('metric');
  const [sortField, setSortField] = useState('win_rate');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [tagFilter, setTagFilter] = useState('');
  const [copied, setCopied] = useState('');
  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }),
    []
  );
  const formatPercent = (value?: string) => {
    if (!value) return '--';
    const num = Number(value);
    if (Number.isNaN(num)) return '--';
    const sign = num > 0 ? '+' : '';
    return `${sign}${(num * 100).toFixed(1)}%`;
  };
  const navigate = useNavigate();
  const sortOptions = sortMode === 'metric' ? METRIC_SORT_FIELDS : sortMode === 'portfolio' ? PORTFOLIO_SORT_FIELDS : AI_SORT_FIELDS;

  const { data, isFetching, error } = useQuery<WalletListResponse>({
    queryKey: ['wallets', { search, status, page, period, sortField, sortOrder, tagFilter }],
    queryFn: () =>
      apiGet<WalletListResponse>('/wallets', {
        search: search || undefined,
        status: status || undefined,
        tag: tagFilter || undefined,
        period,
        sort_key: sortField,
        sort_order: sortOrder,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  const { data: tagOptions } = useQuery<TagResponse[]>({
    queryKey: ['wallet-tags'],
    queryFn: () => apiGet<TagResponse[]>('/tags'),
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
            <select
              value={tagFilter}
              onChange={(e) => {
                setTagFilter(e.target.value);
                setPage(0);
              }}
            >
              <option value="">全部标签</option>
              {tagOptions?.map((tag) => (
                <option key={tag.id} value={tag.name}>
                  {tag.name}
                </option>
              ))}
            </select>
            <div className="toggle-group">
              <button
                className={`btn small ${sortMode === 'metric' ? 'primary' : 'ghost'}`}
                onClick={() => {
                  setSortMode('metric');
                  setSortField(METRIC_SORT_FIELDS[0].value);
                }}
              >
                系统指标
              </button>
              <button
                className={`btn small ${sortMode === 'portfolio' ? 'primary' : 'ghost'}`}
                onClick={() => {
                  setSortMode('portfolio');
                  setSortField(PORTFOLIO_SORT_FIELDS[0].value);
                }}
              >
                官方指标
              </button>
              <button
                className={`btn small ${sortMode === 'ai' ? 'primary' : 'ghost'}`}
                onClick={() => {
                  setSortMode('ai');
                  setSortField(AI_SORT_FIELDS[0].value);
                }}
              >
                AI 指标
              </button>
            </div>
            <select value={sortField} onChange={(e) => setSortField(e.target.value)}>
              {sortOptions.map((field) => (
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
                <th>活跃天数</th>
                <th>同步阶段</th>
                <th>标签</th>
                <th>备注</th>
                <th>胜率</th>
                <th>累计盈亏</th>
                <th>30日收益率</th>
              <th>30日回撤</th>
              <th>AI 推荐</th>
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
                    {wallet.active_days != null ? `${wallet.active_days}天` : '--'}
                  </td>
                  <td>
                    <div className="status-stack">
                      <span className={`status ${wallet.sync_status}`}>同步:{wallet.sync_status}</span>
                      <span className={`status ${wallet.score_status}`}>评分:{wallet.score_status}</span>
                      <span className={`status ${wallet.ai_status}`}>AI:{wallet.ai_status}</span>
                    </div>
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
                  <td>{wallet.note || <span className="muted">-</span>}</td>
                  <td>{formatPercent(wallet.metric?.win_rate as string)}</td>
                  <td>
                    {wallet.metric?.total_pnl ? currencyFormatter.format(Number(wallet.metric.total_pnl)) : '--'}
                  </td>
                  <td>
                    {formatPercent(wallet.portfolio?.month?.return_pct ?? wallet.portfolio?.week?.return_pct)}
                  </td>
                  <td>
                    {formatPercent(wallet.portfolio?.month?.max_drawdown_pct)}
                  </td>
                  <td>
                    {wallet.ai_analysis ? (
                      <div>
                        <div>{wallet.ai_analysis.follow_ratio != null ? `${wallet.ai_analysis.follow_ratio}%` : '--'}</div>
                        <div className="muted">{wallet.ai_analysis.style ?? ''}</div>
                      </div>
                    ) : (
                      <span className="muted">未生成</span>
                    )}
                  </td>
                  <td>
                    <button className="btn small" onClick={() => navigate(`/wallets/${wallet.address}`)}>
                      查看
                    </button>
                  </td>
                </tr>
              ))}
              {!wallets.length && (
                <tr>
                  <td colSpan={9} className="muted">
                    暂无数据，先去
                    <button className="btn small" style={{ marginLeft: '0.5rem' }} onClick={() => navigate('/wallets/import')}>
                      批量导入
                    </button>
                    或调整筛选条件。
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
