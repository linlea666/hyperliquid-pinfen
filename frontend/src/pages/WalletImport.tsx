import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiGet, apiPost } from '../api/client';
import type { WalletImportHistoryResponse, WalletImportResponse } from '../types';

function parseAddresses(text: string): string[] {
  return text
    .split(/[\s,;]+/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

export default function WalletImport() {
  const navigate = useNavigate();
  const [rawInput, setRawInput] = useState('');
  const [tags, setTags] = useState('');
  const [dryRun, setDryRun] = useState(true);
  const [allowDuplicates, setAllowDuplicates] = useState(false);
  const [result, setResult] = useState<WalletImportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { data: history, refetch: refetchHistory } = useQuery<WalletImportHistoryResponse>({
    queryKey: ['wallet-import-history'],
    queryFn: () => apiGet<WalletImportHistoryResponse>('/wallets/import/history', { limit: 10 }),
  });

  const handleFile = (file: File | null) => {
    if (!file) return;
    file.text().then((content) => {
      setRawInput((prev) => (prev ? `${prev}\n${content}` : content));
    });
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    try {
      const addresses = parseAddresses(rawInput);
      if (!addresses.length) {
        setError('请先输入钱包地址');
        setLoading(false);
        return;
      }
      const payload = {
        addresses,
        tags: parseAddresses(tags),
        dry_run: dryRun,
        allow_duplicates: allowDuplicates,
      };
      const res = await apiPost<WalletImportResponse>('/wallets/import', payload);
      setResult(res);
      await refetchHistory();
    } catch (err: any) {
      setError(err.message || '导入失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <section className="card">
        <h2>钱包批量导入</h2>
        <p className="muted">支持粘贴文本或上传包含钱包地址的 TXT/CSV 文件（以逗号、换行、空格等分隔）。</p>
        <div className="import-grid">
          <label className="full-span">
            地址列表
            <textarea value={rawInput} onChange={(e) => setRawInput(e.target.value)} rows={8} placeholder="一行一个或使用逗号分隔" />
          </label>
          <label>
            导入文件
            <input type="file" accept=".txt,.csv" onChange={(e) => handleFile(e.target.files?.[0] ?? null)} />
          </label>
          <label>
            标签（可选，逗号分隔）
            <input value={tags} onChange={(e) => setTags(e.target.value)} placeholder="vip,ai" />
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
            试运行（不真正写入，只查看结果）
          </label>
          <label className="checkbox-row">
            <input type="checkbox" checked={allowDuplicates} onChange={(e) => setAllowDuplicates(e.target.checked)} />
            允许重复地址
          </label>
        </div>
        {error && <p className="error">{error}</p>}
        <div className="header-actions">
          <button className="btn secondary" onClick={() => navigate('/wallets')}>
            返回列表
          </button>
          <button className="btn primary" disabled={loading} onClick={handleSubmit}>
            {loading ? '处理中...' : '提交导入'}
          </button>
        </div>
      </section>

      {result && (
        <section className="card">
          <h3>导入结果</h3>
          <p className="muted">
            共 {result.requested} 条，成功 {result.imported} 条，跳过 {result.skipped} 条，模式：
            {result.dry_run ? '试运行' : '正式导入'} ｜ 标签：{result.tags.join(', ') || '无'} ｜ 提交人：
            {result.created_by ?? '当前用户'} ｜ 时间：{result.created_at ? new Date(result.created_at).toLocaleString() : '--'}
          </p>
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>地址</th>
                  <th>状态</th>
                  <th>说明</th>
                  <th>标签</th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((item) => (
                  <tr key={`${item.address}-${item.status}`}>
                    <td>{item.address}</td>
                    <td>{item.status}</td>
                    <td>{item.message ?? '-'}</td>
                    <td>{item.tags_applied?.join(', ') || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="card">
        <h3>最近导入记录</h3>
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>来源</th>
                <th>标签</th>
                <th>操作人</th>
                <th>时间</th>
              </tr>
            </thead>
            <tbody>
              {history?.items.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.source}</td>
                  <td>{item.tags.join(', ') || '-'}</td>
                  <td>{item.created_by ?? '--'}</td>
                  <td>{new Date(item.created_at).toLocaleString()}</td>
                </tr>
              ))}
              {!history?.items?.length && (
                <tr>
                  <td colSpan={5} className="muted">
                    暂无记录
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
