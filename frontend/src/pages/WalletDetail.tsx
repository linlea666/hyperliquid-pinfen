import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import MetricCard from '../components/MetricCard';
import { apiGet, apiPost } from '../api/client';
import { showToast } from '../utils/toast';
import type { LatestRecords, WalletSummary, WalletNoteResponse, PaginatedResponse } from '../types';
import type { AIAnalysisResponse } from '../types';

const PERIOD_OPTIONS = [
  { label: '24小时', value: '1d' },
  { label: '7天', value: '7d' },
  { label: '30天', value: '30d' },
  { label: '90天', value: '90d' },
  { label: '1年', value: '1y' },
  { label: '全部', value: 'all' },
];

export default function WalletDetail() {
  const { address } = useParams();
  const [copied, setCopied] = useState(false);
  const [noteDraft, setNoteDraft] = useState('');
  const [savingNote, setSavingNote] = useState(false);
  const [selectedPeriod, setSelectedPeriod] = useState('30d');
  const [tradePage, setTradePage] = useState(0);
  const [ledgerPage, setLedgerPage] = useState(0);
  const [orderPage, setOrderPage] = useState(0);
  const [historyTab, setHistoryTab] = useState<'trades' | 'ledger' | 'orders'>('trades');
  const PAGE_SIZE = 20;

  const { data: detail, isLoading, error } = useQuery<WalletSummary>({
    queryKey: ['wallet', address],
    queryFn: () => apiGet<WalletSummary>(`/wallets/${address}`),
    enabled: Boolean(address),
  });

  const { data: latest } = useQuery<LatestRecords>({
    queryKey: ['wallet-latest', address],
    queryFn: () => apiGet<LatestRecords>(`/wallets/latest/${address}`, { limit: 50 }),
    enabled: Boolean(address),
  });

  const { data: aiAnalysis, refetch: refetchAI, isFetching: aiLoading } = useQuery<AIAnalysisResponse | undefined>({
    queryKey: ['wallet-ai', address],
    queryFn: async () => {
      try {
        return await apiGet<AIAnalysisResponse>(`/wallets/${address}/ai`);
      } catch {
        return undefined;
      }
    },
    enabled: Boolean(address),
    retry: 0,
  });
  const { data: tradesData } = useQuery<PaginatedResponse<any>>({
    queryKey: ['wallet-fills', address, tradePage],
    queryFn: () => apiGet('/wallets/fills', { address, limit: PAGE_SIZE, offset: tradePage * PAGE_SIZE }),
    enabled: Boolean(address),
  });
  const { data: ledgerData } = useQuery<PaginatedResponse<any>>({
    queryKey: ['wallet-ledger', address, ledgerPage],
    queryFn: () => apiGet('/wallets/ledger', { address, limit: PAGE_SIZE, offset: ledgerPage * PAGE_SIZE }),
    enabled: Boolean(address),
  });
  const { data: orderData } = useQuery<PaginatedResponse<any>>({
    queryKey: ['wallet-orders', address, orderPage],
    queryFn: () => apiGet('/wallets/orders', { address, limit: PAGE_SIZE, offset: orderPage * PAGE_SIZE }),
    enabled: Boolean(address),
  });
  useEffect(() => {
    setNoteDraft(detail?.note ?? '');
  }, [detail?.note]);
  const currencyFormatter = useMemo(
    () => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 2 }),
    []
  );
  const numberFormatter = useMemo(() => new Intl.NumberFormat('en-US', { maximumFractionDigits: 2 }), []);
  const formatPercent = (value?: string | number, fraction = true) => {
    if (value === undefined || value === null) return '--';
    const num = Number(value);
    if (Number.isNaN(num)) {
      return '--';
    }
    return fraction ? `${(num * 100).toFixed(1)}%` : `${num.toFixed(1)}%`;
  };

  const handleSaveNote = async () => {
    if (!address) return;
    try {
      setSavingNote(true);
      const payload: WalletNoteResponse = await apiPost(`/wallets/${address}/note`, { note: noteDraft });
      setNoteDraft(payload.note ?? '');
      showToast('备注已保存', 'success');
    } catch (err: any) {
      showToast(err?.message ?? '保存失败', 'error');
    } finally {
      setSavingNote(false);
    }
  };

  const chartData = useMemo(() => {
    let cumulative = 0;
    return (
      latest?.fills
        ?.slice()
        .reverse()
        .map((fill) => {
          const pnl = Number(fill.closed_pnl ?? 0);
          cumulative += pnl;
          const ts = Number(fill.time_ms ?? fill.time ?? 0);
          return {
            time: ts ? new Date(ts).toLocaleDateString() : '',
            pnl: cumulative,
          };
        }) ?? []
    );
  }, [latest]);
  const periodStats = detail?.metric?.details?.periods ?? {};
  const selectedStats = periodStats[selectedPeriod];
  const portfolioStats = detail?.portfolio ?? {};
  const portfolioWeek = portfolioStats.week;
  const portfolioMonth = portfolioStats.month;
  const portfolioAll = portfolioStats.allTime;
  const trades = tradesData?.items ?? [];
  const tradeTotal = tradesData?.total ?? trades.length;
  const tradeTotalPages = Math.max(1, Math.ceil(tradeTotal / PAGE_SIZE));
  const ledgerItems = ledgerData?.items ?? [];
  const ledgerTotal = ledgerData?.total ?? ledgerItems.length;
  const ledgerTotalPages = Math.max(1, Math.ceil(ledgerTotal / PAGE_SIZE));
  const orderItems = orderData?.items ?? [];
  const orderTotal = orderData?.total ?? orderItems.length;
  const orderTotalPages = Math.max(1, Math.ceil(orderTotal / PAGE_SIZE));
  const currentPositions = useMemo(() => {
    if (!latest?.positions?.length) return [];
    const seen = new Map<string, any>();
    for (const pos of latest.positions) {
      const key = pos.coin || pos.symbol || pos.id;
      if (!seen.has(key)) {
        seen.set(key, pos);
      }
    }
    return Array.from(seen.values());
  }, [latest]);

  if (isLoading) {
    return <div className="card">加载中...</div>;
  }

  if (error || !detail) {
    return <div className="card error">加载失败：{(error as Error)?.message ?? '钱包不存在'}</div>;
  }

  return (
    <div className="page">
      <section className="card">
        <div className="address-cell">
          <h2>{detail.address}</h2>
          <button
            className="btn ghost small"
            onClick={async () => {
              await navigator.clipboard.writeText(detail.address);
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
            }}
          >
            {copied ? '已复制' : '复制地址'}
          </button>
        </div>
        <p className="muted">
          状态：<span className={`status ${detail.status}`}>{detail.status}</span> ｜{' '}
          {detail.last_synced_at ? `最近同步：${new Date(detail.last_synced_at).toLocaleString()}` : '未同步'}
        </p>
        <p className="muted">
          {detail.first_trade_time ? `首次交易：${new Date(detail.first_trade_time).toLocaleString()}` : '尚未产生交易'} ｜ 活跃天数：
          {detail.active_days ?? '--'}
        </p>
        <p className="muted">
          标签：
          {detail.tags?.length ? (
            detail.tags.map((tag: any) => (
              <span
                key={tag.id ?? tag}
                className="tag-chip"
                style={{ background: tag.color || 'rgba(255,255,255,0.1)' }}
              >
                {tag.name ?? tag}
              </span>
            ))
          ) : (
            '无'
          )}
        </p>
      </section>

      <section className="grid-4">
        <MetricCard title="胜率" value={formatPercent(detail.metric?.win_rate)} description="Win Rate" />
        <MetricCard
          title="总盈亏"
          value={detail.metric?.total_pnl ? currencyFormatter.format(Number(detail.metric.total_pnl)) : '--'}
          description="Closed PnL"
        />
        <MetricCard
          title="平均盈亏"
          value={detail.metric?.avg_pnl ? currencyFormatter.format(Number(detail.metric.avg_pnl)) : '--'}
          description="Per Trade"
        />
        <MetricCard title="评分" value={detail.score?.score ?? '--'} description={detail.score?.level ?? '未评分'} />
      </section>

      {Object.keys(portfolioStats).length > 0 && (
        <section className="card mt">
          <h3>官方 Portfolio 指标</h3>
          <div className="grid-4">
            <MetricCard title="7日收益率" value={formatPercent(portfolioWeek?.return_pct)} description="官方权益曲线" />
            <MetricCard title="30日收益率" value={formatPercent(portfolioMonth?.return_pct)} description="官方权益曲线" />
            <MetricCard title="30日最大回撤" value={formatPercent(portfolioMonth?.max_drawdown_pct)} description="Drawdown" />
            <MetricCard title="历史收益率" value={formatPercent(portfolioAll?.return_pct)} description="All-time Return" />
          </div>
        </section>
      )}

      <section className="card mt">
        <h3>钱包备注</h3>
        <textarea
          className="note-editor"
          value={noteDraft}
          placeholder="输入备注，便于团队内部识别。"
          onChange={(e) => setNoteDraft(e.target.value)}
        />
        <div className="header-actions">
          <button className="btn primary" onClick={handleSaveNote} disabled={savingNote}>
            {savingNote ? '保存中...' : '保存备注'}
          </button>
        </div>
      </section>

      <section className="card mt">
        <h3>当前持仓</h3>
        {currentPositions.length ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>合约</th>
                  <th>仓位</th>
                  <th>开仓均价</th>
                  <th>持仓价值</th>
                  <th>未实现盈亏</th>
                  <th>ROE</th>
                </tr>
              </thead>
              <tbody>
                {currentPositions.map((pos) => (
                  <tr key={`${pos.coin}-${pos.time_ms}`}>
                    <td>{pos.coin}</td>
                    <td>{numberFormatter.format(Number(pos.szi ?? 0))}</td>
                    <td>{numberFormatter.format(Number(pos.entry_px ?? 0))}</td>
                    <td>{numberFormatter.format(Number(pos.pos_value ?? 0))}</td>
                    <td className={Number(pos.unrealized_pnl ?? 0) >= 0 ? 'text-success' : 'text-danger'}>
                      {numberFormatter.format(Number(pos.unrealized_pnl ?? 0))}
                    </td>
                    <td>{formatPercent(Number(pos.roe ?? 0), false)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="muted">暂无持仓信息</p>
        )}
      </section>

      <section className="card mt">
        <h3>收益表现</h3>
        <div className="period-toggle">
          {PERIOD_OPTIONS.map((option) => (
            <button
              key={option.value}
              className={`btn small ${selectedPeriod === option.value ? 'primary' : 'ghost'}`}
              onClick={() => setSelectedPeriod(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
        {selectedStats ? (
          <div className="period-summary">
            <div>
              <p className="metric-title">收益额</p>
              <p className="metric-value">{currencyFormatter.format(selectedStats.pnl)}</p>
            </div>
            <div>
              <p className="metric-title">收益率</p>
              <p className="metric-value">
                {selectedStats.return >= 0 ? '+' : ''}
                {selectedStats.return.toFixed(2)}%
              </p>
            </div>
            <div>
              <p className="metric-title">成交笔数</p>
              <p className="metric-value">{selectedStats.trades}</p>
            </div>
          </div>
        ) : (
          <p className="muted">暂无该周期数据</p>
        )}
      </section>

      <section className="card mt">
        <h3>AI 分析</h3>
        {aiAnalysis ? (
          <>
            <p>风格：{aiAnalysis.style}</p>
            <p>得分：{aiAnalysis.score ?? '--'} ｜ 推荐跟单比例：{aiAnalysis.follow_ratio ?? '--'}%</p>
            <p>优势：{aiAnalysis.strengths}</p>
            <p>风险：{aiAnalysis.risks}</p>
            <p>建议：{aiAnalysis.suggestion}</p>
          </>
        ) : (
          <button
            className="btn primary"
            disabled={aiLoading}
            onClick={async () => {
              if (!address) return;
              await apiPost<AIAnalysisResponse>(`/wallets/${address}/ai`);
              await refetchAI();
            }}
          >
            {aiLoading ? '生成中...' : '生成 AI 分析'}
          </button>
        )}
      </section>

      <section className="card mt">
        <h3>历史记录</h3>
        <div className="period-toggle">
          <button className={`btn small ${historyTab === 'trades' ? 'primary' : 'ghost'}`} onClick={() => setHistoryTab('trades')}>
            交易记录
          </button>
          <button className={`btn small ${historyTab === 'ledger' ? 'primary' : 'ghost'}`} onClick={() => setHistoryTab('ledger')}>
            资金流水
          </button>
          <button className={`btn small ${historyTab === 'orders' ? 'primary' : 'ghost'}`} onClick={() => setHistoryTab('orders')}>
            订单状态
          </button>
        </div>
        <div className="table-wrapper mt">
          <table>
            <thead>
              {historyTab === 'trades' && (
                <tr>
                  <th>时间</th>
                  <th>合约</th>
                  <th>方向</th>
                  <th>价格</th>
                  <th>数量</th>
                  <th>盈亏</th>
                </tr>
              )}
              {historyTab === 'ledger' && (
                <tr>
                  <th>时间</th>
                  <th>类型</th>
                  <th>金额 (USDC)</th>
                  <th>来源</th>
                </tr>
              )}
              {historyTab === 'orders' && (
                <tr>
                  <th>时间</th>
                  <th>合约</th>
                  <th>方向</th>
                  <th>价格</th>
                  <th>数量</th>
                  <th>状态</th>
                </tr>
              )}
            </thead>
            <tbody>
              {historyTab === 'trades' &&
                (trades.length ? (
                  trades.map((item) => (
                    <tr key={`${item.hash}-${item.time_ms}`}>
                      <td>{item.time_ms ? new Date(Number(item.time_ms)).toLocaleString() : '-'}</td>
                      <td>{item.coin}</td>
                      <td>{item.dir || item.side}</td>
                      <td>{item.px}</td>
                      <td>{item.sz}</td>
                      <td className={Number(item.closed_pnl || 0) >= 0 ? 'text-success' : 'text-danger'}>
                        {numberFormatter.format(Number(item.closed_pnl || 0))}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="muted">
                      暂无交易记录
                    </td>
                  </tr>
                ))}
              {historyTab === 'ledger' &&
                (ledgerItems.length ? (
                  ledgerItems.map((item) => (
                    <tr key={`${item.hash}-${item.time_ms}`}>
                      <td>{item.time_ms ? new Date(Number(item.time_ms)).toLocaleString() : '-'}</td>
                      <td>{item.delta_type}</td>
                      <td>{numberFormatter.format(Number(item.usdc_value ?? item.amount ?? 0))}</td>
                      <td>{item.vault || item.token || '-'}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} className="muted">
                      暂无资金流水
                    </td>
                  </tr>
                ))}
              {historyTab === 'orders' &&
                (orderItems.length ? (
                  orderItems.map((item) => (
                    <tr key={`${item.hash || item.oid}-${item.time_ms}`}>
                      <td>{item.time_ms ? new Date(Number(item.time_ms)).toLocaleString() : '-'}</td>
                      <td>{item.coin}</td>
                      <td>{item.side}</td>
                      <td>{item.limit_px ?? item.px}</td>
                      <td>{item.sz}</td>
                      <td>{item.status ?? item.order_type}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={6} className="muted">
                      暂无订单记录
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
        <div className="pagination">
          {historyTab === 'trades' && (
            <>
              <button className="btn small" onClick={() => setTradePage((p) => Math.max(p - 1, 0))} disabled={tradePage === 0}>
                上一页
              </button>
              <span>
                第 {tradePage + 1} / {tradeTotalPages} 页
              </span>
              <button
                className="btn small"
                onClick={() => setTradePage((p) => (p + 1 < tradeTotalPages ? p + 1 : p))}
                disabled={tradePage + 1 >= tradeTotalPages}
              >
                下一页
              </button>
            </>
          )}
          {historyTab === 'ledger' && (
            <>
              <button className="btn small" onClick={() => setLedgerPage((p) => Math.max(p - 1, 0))} disabled={ledgerPage === 0}>
                上一页
              </button>
              <span>
                第 {ledgerPage + 1} / {ledgerTotalPages} 页
              </span>
              <button
                className="btn small"
                onClick={() => setLedgerPage((p) => (p + 1 < ledgerTotalPages ? p + 1 : p))}
                disabled={ledgerPage + 1 >= ledgerTotalPages}
              >
                下一页
              </button>
            </>
          )}
          {historyTab === 'orders' && (
            <>
              <button className="btn small" onClick={() => setOrderPage((p) => Math.max(p - 1, 0))} disabled={orderPage === 0}>
                上一页
              </button>
              <span>
                第 {orderPage + 1} / {orderTotalPages} 页
              </span>
              <button
                className="btn small"
                onClick={() => setOrderPage((p) => (p + 1 < orderTotalPages ? p + 1 : p))}
                disabled={orderPage + 1 >= orderTotalPages}
              >
                下一页
              </button>
            </>
          )}
        </div>
      </section>

      <section className="card mt">
        <h3>盈亏推进</h3>
        {chartData.length ? (
          <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <XAxis dataKey="time" hide />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="pnl" stroke="#7c3aed" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p className="muted">暂无成交数据</p>
        )}
      </section>

      <section className="card mt">
        <h3>最近账本事件</h3>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th>类型</th>
                <th>金额 (USDC)</th>
                <th>备注</th>
              </tr>
            </thead>
            <tbody>
              {latest?.ledger?.map((item) => (
                <tr key={`${item.hash}-${item.time_ms}`}>
                  <td>{item.time_ms ? new Date(Number(item.time_ms)).toLocaleString() : '-'}</td>
                  <td>{item.delta_type}</td>
                  <td>{item.usdc_value ?? item.amount ?? '--'}</td>
                  <td>{item.vault || item.token || '-'}</td>
                </tr>
              ))}
              {!latest?.ledger?.length && (
                <tr>
                  <td colSpan={4} className="muted">
                    暂无数据
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
