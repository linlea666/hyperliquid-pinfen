import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import MetricCard from '../components/MetricCard';
import { apiGet, apiPost } from '../api/client';
import { showToast } from '../utils/toast';
import type { LatestRecords, WalletSummary, WalletNoteResponse } from '../types';
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
  const { data: tradesData } = useQuery<{ items: any[]; total: number }>({
    queryKey: ['wallet-fills', address, tradePage],
    queryFn: () => apiGet('/wallets/fills', { address, limit: 20, offset: tradePage * 20 }),
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
  const trades = tradesData?.items ?? [];
  const tradeTotal = tradesData?.total ?? trades.length;
  const tradeTotalPages = Math.max(1, Math.ceil(tradeTotal / 20));

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
        <h3>历史交易</h3>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>时间</th>
                <th>合约</th>
                <th>方向</th>
                <th>价格</th>
                <th>数量</th>
                <th>盈亏</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((item) => (
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
              ))}
              {!trades.length && (
                <tr>
                  <td colSpan={6} className="muted">
                    暂无交易记录
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="pagination">
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
