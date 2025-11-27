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

function authHeaders(): Record<string, string> {
  if (typeof window === 'undefined') return {};
  const token = window.localStorage.getItem('authToken');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function apiGet<T>(path: string, params?: Record<string, any>): Promise<T> {
  const res = await fetch(`${API_BASE}${path}${buildQuery(params)}`, {
    headers: {
      ...authHeaders(),
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
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    throw new Error(`请求失败：${res.statusText}`);
  }
  return res.json();
}

export async function apiPut<T>(path: string, body?: Record<string, any>): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    throw new Error(`请求失败：${res.statusText}`);
  }
  return res.json();
}

export async function apiPostPublic<T>(path: string, body?: Record<string, any>): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    throw new Error(`请求失败：${res.statusText}`);
  }
  return res.json();
}
