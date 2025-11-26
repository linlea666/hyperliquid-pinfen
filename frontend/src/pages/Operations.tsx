import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api/client';
import { showToast } from '../utils/toast';
import type {
  OperationsReport,
  TaskListResponse,
  Schedule,
  ProcessingLogListResponse,
  ProcessingLog,
  ProcessingSummaryResponse,
} from '../types';

export default function Operations() {
  const { data: report } = useQuery<OperationsReport>({
    queryKey: ['operations-report'],
    queryFn: () => apiGet<OperationsReport>('/reports/operations'),
  });

  const { data: tasks, isError: tasksError } = useQuery<TaskListResponse>({
    queryKey: ['tasks'],
    queryFn: () => apiGet<TaskListResponse>('/tasks'),
  });

  const { data: schedules, refetch: refetchSchedules } = useQuery<Schedule[]>({
    queryKey: ['schedules'],
    queryFn: () => apiGet<Schedule[]>('/schedules'),
  });

  const [activeTab, setActiveTab] = useState<'overview' | 'processing' | 'schedules'>('overview');
  const [stageFilter, setStageFilter] = useState<'all' | 'sync' | 'score' | 'ai'>('all');

  const {
    data: processingLogs,
    refetch: refetchProcessingLogs,
  } = useQuery<ProcessingLogListResponse>({
    queryKey: ['processing-logs', stageFilter],
    queryFn: () =>
      apiGet<ProcessingLogListResponse>('/processing/logs', {
        stage: stageFilter === 'all' ? undefined : stageFilter,
        limit: 30,
      }),
  });

  const {
    data: processingSummary,
    refetch: refetchProcessingSummary,
  } = useQuery<ProcessingSummaryResponse>({
    queryKey: ['processing-summary'],
    queryFn: () => apiGet<ProcessingSummaryResponse>('/processing/summary'),
  });

  const [newSchedule, setNewSchedule] = useState({
    name: '',
    job_type: 'leaderboard_run_all',
    cron: '0 * * * *',
    address: '',
  });

  const handleRetry = async (log: ProcessingLog) => {
    try {
      await apiPost('/processing/retry', { address: log.wallet_address, stage: log.stage });
      showToast('已重新排队', 'success');
      await refetchProcessingLogs();
      await refetchProcessingSummary();
    } catch (err: any) {
      showToast(err?.message ?? '重试失败', 'error');
    }
  };

  const createSchedule = async () => {
    const payload: any = {
      name: newSchedule.name || (newSchedule.job_type === 'leaderboard_run_all' ? '榜单刷新' : '钱包同步'),
      job_type: newSchedule.job_type,
      cron: newSchedule.cron,
      payload: newSchedule.job_type === 'wallet_sync' ? { address: newSchedule.address } : undefined,
    };
    try {
      await apiPost('/schedules', payload);
      await refetchSchedules();
      showToast('调度已创建', 'success');
    } catch (err: any) {
      showToast(err?.message ?? '创建失败', 'error');
    }
  };

  return (
    <div className="page">
      <section className="card">
        <h2>运营与处理中心</h2>
        <p className="muted">查看任务运行状况、处理流水并管理调度。</p>
        <div className="tab-bar">
          <button className={`tab-btn ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
            仪表盘
          </button>
          <button className={`tab-btn ${activeTab === 'processing' ? 'active' : ''}`} onClick={() => setActiveTab('processing')}>
            处理流水
          </button>
          <button className={`tab-btn ${activeTab === 'schedules' ? 'active' : ''}`} onClick={() => setActiveTab('schedules')}>
            自动调度
          </button>
        </div>
      </section>

      {activeTab === 'overview' && (
        <>
          <section className="card">
            <h3>运营概览</h3>
            <div className="grid-4">
              <div className="metric-card">
                <p className="metric-title">总钱包</p>
                <p className="metric-value">{report?.wallet_total ?? '--'}</p>
              </div>
              <div className="metric-card">
                <p className="metric-title">已同步</p>
                <p className="metric-value">{report ? `${report.synced_wallets}/${report.wallet_total}` : '--'}</p>
              </div>
              <div className="metric-card">
                <p className="metric-title">任务运行中</p>
                <p className="metric-value">{report?.tasks_running ?? '--'}</p>
              </div>
              <div className="metric-card">
                <p className="metric-title">通知已发送</p>
                <p className="metric-value">{report?.notifications_sent ?? '--'}</p>
              </div>
            </div>
            <p className="muted">最近同步时间：{report?.last_sync ? new Date(report.last_sync).toLocaleString() : '无'}</p>
          </section>

          <section className="card">
            <h3>任务监控</h3>
            {tasksError && <p className="error">任务列表加载失败，请稍后重试。</p>}
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>类型</th>
                    <th>状态</th>
                    <th>开始时间</th>
                    <th>结束时间</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks?.items.map((task) => (
                    <tr key={task.id}>
                      <td>{task.id}</td>
                      <td>{task.task_type}</td>
                      <td>{task.status}</td>
                      <td>{new Date(task.started_at).toLocaleString()}</td>
                      <td>{task.finished_at ? new Date(task.finished_at).toLocaleString() : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      {activeTab === 'processing' && (
        <>
          <section className="card">
            <h3>分析处理概览</h3>
            <div className="grid-4">
              <div className="metric-card">
                <p className="metric-title">处理队列</p>
                <p className="metric-value">{processingSummary?.queue_size ?? '--'}</p>
                <p className="metric-desc">RQ 等待任务数</p>
              </div>
              <div className="metric-card">
                <p className="metric-title">待重算钱包</p>
                <p className="metric-value">{processingSummary?.pending_rescore ?? '--'}</p>
                <p className="metric-desc">next_score_due 到期</p>
              </div>
            </div>
            <div className="table-wrapper mt">
              <table>
                <thead>
                  <tr>
                    <th>阶段</th>
                    <th>待处理</th>
                    <th>运行中</th>
                    <th>成功</th>
                    <th>失败</th>
                  </tr>
                </thead>
                <tbody>
                  {processingSummary?.stages.map((stage) => {
                    const successKey =
                      stage.stage === 'sync' ? 'synced' : stage.stage === 'score' ? 'scored' : 'completed';
                    return (
                      <tr key={stage.stage}>
                        <td>{stage.stage}</td>
                        <td>{stage.counts.pending ?? 0}</td>
                        <td>{stage.counts.running ?? 0}</td>
                        <td>{stage.counts[successKey] ?? 0}</td>
                        <td>{stage.counts.failed ?? 0}</td>
                      </tr>
                    );
                  })}
                  {!processingSummary?.stages.length && (
                    <tr>
                      <td colSpan={5} className="muted">
                        暂无统计
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
            <div className="mt">
              <h4>最近失败</h4>
              <ul className="muted">
                {processingSummary?.last_failed?.length ? (
                  processingSummary.last_failed.map((log) => (
                    <li key={log.id}>
                      {log.wallet_address} · {log.stage} · {log.error || '未知错误'} ·{' '}
                      {log.finished_at ? new Date(log.finished_at).toLocaleString() : ''}
                    </li>
                  ))
                ) : (
                  <li>暂无失败记录</li>
                )}
              </ul>
            </div>
          </section>

          <section className="card">
            <h3>处理流水</h3>
            <div className="filters">
              <select value={stageFilter} onChange={(e) => setStageFilter(e.target.value as any)}>
                <option value="all">全部阶段</option>
                <option value="sync">同步</option>
                <option value="score">评分</option>
                <option value="ai">AI 分析</option>
              </select>
            </div>
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>钱包</th>
                    <th>阶段</th>
                    <th>状态</th>
                    <th>尝试</th>
                    <th>来源</th>
                    <th>开始时间</th>
                    <th>结束时间</th>
                    <th>错误信息</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {processingLogs?.items.map((log) => (
                    <tr key={log.id}>
                      <td>{log.wallet_address}</td>
                      <td>{log.stage}</td>
                      <td>{log.status}</td>
                      <td>{log.attempt}</td>
                      <td>{log.scheduled_by}</td>
                      <td>{log.started_at ? new Date(log.started_at).toLocaleString() : '-'}</td>
                      <td>{log.finished_at ? new Date(log.finished_at).toLocaleString() : '-'}</td>
                      <td className="muted">{log.error ?? '-'}</td>
                      <td>
                        <button className="btn small" onClick={() => handleRetry(log)}>
                          重试
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!processingLogs?.items.length && (
                    <tr>
                      <td colSpan={9} className="muted">
                        暂无流水
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

  {activeTab === 'schedules' && (
        <section className="card">
          <h3>自动调度</h3>
          <div className="filters">
            <input
              placeholder="任务名称"
              value={newSchedule.name}
              onChange={(e) => setNewSchedule((prev) => ({ ...prev, name: e.target.value }))}
            />
            <select
              value={newSchedule.job_type}
              onChange={(e) => setNewSchedule((prev) => ({ ...prev, job_type: e.target.value }))}
            >
              <option value="leaderboard_run_all">刷新全部榜单</option>
              <option value="wallet_sync">同步指定钱包</option>
            </select>
            <input
              placeholder="Cron 表达式"
              value={newSchedule.cron}
              onChange={(e) => setNewSchedule((prev) => ({ ...prev, cron: e.target.value }))}
            />
            {newSchedule.job_type === 'wallet_sync' && (
              <input
                placeholder="钱包地址"
                value={newSchedule.address}
                onChange={(e) => setNewSchedule((prev) => ({ ...prev, address: e.target.value }))}
              />
            )}
            <button className="btn primary" onClick={createSchedule}>
              创建调度
            </button>
          </div>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>名称</th>
                  <th>类型</th>
                  <th>Cron</th>
                  <th>负载</th>
                </tr>
              </thead>
              <tbody>
                {schedules?.map((job) => (
                  <tr key={job.id}>
                    <td>{job.name}</td>
                    <td>{job.job_type}</td>
                    <td>{job.cron}</td>
                    <td>{job.payload ? JSON.stringify(job.payload) : '-'}</td>
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
