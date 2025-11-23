import { useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import MetricCard from '../components/MetricCard';
import { apiGet, apiPost } from '../api/client';
import type { LatestRecords, WalletSummary } from '../types';
import type { AIAnalysisResponse } from '../types';

export default function WalletDetail() {
  const { address } = useParams();

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

  if (isLoading) {
    return <div className="card">加载中...</div>;
  }

  if (error || !detail) {
    return <div className="card error">加载失败：{(error as Error)?.message ?? '钱包不存在'}</div>;
  }

  return (
    <div className="page">
      <section className="card">
        <h2>{detail.address}</h2>
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
        <MetricCard title="胜率" value={detail.metric?.win_rate ?? '--'} description="Win Rate" />
        <MetricCard title="总盈亏" value={detail.metric?.total_pnl ?? '--'} description="Closed PnL" />
        <MetricCard title="平均盈亏" value={detail.metric?.avg_pnl ?? '--'} description="Per Trade" />
        <MetricCard title="评分" value={detail.score?.score ?? '--'} description={detail.score?.level ?? '未评分'} />
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
