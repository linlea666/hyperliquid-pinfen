const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

function buildQuery(params?: Record<string, any>) {
  if (!params) return '';
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    search.append(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : '';
}

function adminHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = window.localStorage.getItem('adminToken');
  return token ? { 'X-Admin-Token': token } : {};
}

export async function apiGet<T>(path: string, params?: Record<string, any>): Promise<T> {
  const res = await fetch(`${API_BASE}${path}${buildQuery(params)}`, {
    headers: {
      ...adminHeaders(),
    },
  });
  if (!res.ok) {
    throw new Error(`请求失败：${res.statusText}`);
  }
  return res.json();
}

export async function apiPost<T>(path: string, body?: Record<string, any>): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...adminHeaders() },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    throw new Error(`请求失败：${res.statusText}`);
  }
  return res.json();
}
