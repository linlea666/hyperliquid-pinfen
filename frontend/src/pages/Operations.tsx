import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiGet, apiPost } from '../api/client';
import type { OperationsReport, TaskListResponse, Schedule } from '../types';

export default function Operations() {
  const queryClient = useQueryClient();
  const [tokenInput, setTokenInput] = useState<string>(() => (typeof window !== 'undefined' ? localStorage.getItem('adminToken') ?? '' : ''));
  const [hasToken, setHasToken] = useState<boolean>(() => Boolean(typeof window !== 'undefined' && localStorage.getItem('adminToken')));

  const { data: report } = useQuery<OperationsReport>({
    queryKey: ['operations-report'],
    queryFn: () => apiGet<OperationsReport>('/reports/operations'),
  });

  const { data: tasks, refetch: refetchTasks, isError: tasksError } = useQuery<TaskListResponse>({
    queryKey: ['tasks', hasToken],
    queryFn: () => apiGet<TaskListResponse>('/tasks'),
    enabled: hasToken,
    retry: 0,
  });

  const { data: schedules, refetch: refetchSchedules } = useQuery<Schedule[]>({
    queryKey: ['schedules', hasToken],
    queryFn: () => apiGet<Schedule[]>('/schedules'),
    enabled: hasToken,
    retry: 0,
  });

  const [newSchedule, setNewSchedule] = useState({
    name: '',
    job_type: 'leaderboard_run_all',
    cron: '0 * * * *',
    address: '',
  });

  useEffect(() => {
    if (hasToken) {
      refetchTasks();
    }
  }, [hasToken, refetchTasks]);

  return (
    <div className="page">
      <section className="card">
        <h2>运营概览</h2>
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
        <h3>任务监控（管理员）</h3>
        <div className="filters">
          <input
            placeholder="输入管理员 Token"
            value={tokenInput}
            onChange={(e) => setTokenInput(e.target.value)}
          />
          <button
            className="btn primary"
            onClick={() => {
              if (typeof window === 'undefined') return;
              window.localStorage.setItem('adminToken', tokenInput);
              setHasToken(Boolean(tokenInput));
              queryClient.invalidateQueries({ queryKey: ['tasks'] });
            }}
          >
            保存令牌
          </button>
        </div>
        {!hasToken && <p className="muted">未设置管理员 Token，仅显示公共数据。</p>}
        {tasksError && <p className="error">任务列表加载失败，请检查 Token。</p>}
        {hasToken && (
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
        )}
      </section>

      {hasToken && (
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
            <button
              className="btn primary"
              onClick={async () => {
                const payload: any = {
                  name: newSchedule.name || (newSchedule.job_type === 'leaderboard_run_all' ? '榜单刷新' : '钱包同步'),
                  job_type: newSchedule.job_type,
                  cron: newSchedule.cron,
                  payload: newSchedule.job_type === 'wallet_sync' ? { address: newSchedule.address } : undefined,
                };
                await apiPost('/schedules', payload);
                await refetchSchedules();
              }}
            >
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
