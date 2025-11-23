import { useQuery } from '@tanstack/react-query';
import MetricCard from '../components/MetricCard';
import { apiGet } from '../api/client';
import type { WalletOverview } from '../types';

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['overview'],
    queryFn: () => apiGet<WalletOverview>('/wallets/overview'),
  });

  if (isLoading) {
    return <div className="card">加载中...</div>;
  }

  if (error) {
    return <div className="card error">加载失败：{(error as Error).message}</div>;
  }

  return (
    <div className="page">
      <section className="grid-4">
        <MetricCard title="钱包总数" value={data?.total_wallets ?? '--'} description="已导入钱包数量" />
        <MetricCard
          title="已同步钱包"
          value={`${data?.synced_wallets ?? 0}/${data?.total_wallets ?? 0}`}
          description="完成 Hyperliquid 数据拉取的钱包"
        />
        <MetricCard title="账本事件" value={data?.ledger_events ?? '--'} description="累计资金往来记录" />
        <MetricCard title="成交记录" value={data?.fills ?? '--'} description="累计成交数" />
      </section>

      <section className="card mt">
        <h2>快速指南</h2>
        <ol className="steps">
          <li>在后台导入钱包地址（支持文本/文件/批量标签）。</li>
          <li>执行同步任务（实时或异步）从 Hyperliquid 拉取原始数据。</li>
          <li>运行评分任务，查看钱包指标、榜单与建议。</li>
          <li>在前台页面对比优秀交易员，关注/订阅并生成报告。</li>
        </ol>
        {data?.last_sync && <p className="muted">最近同步时间：{new Date(data.last_sync).toLocaleString()}</p>}
      </section>
    </div>
  );
}
