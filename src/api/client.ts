const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5100';

export async function fetchHealth(): Promise<{ ok?: boolean; status?: string }> {
  const res = await fetch(`${API_BASE}/health`, { method: 'GET' });
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, ...data };
}

export async function fetchSchema(): Promise<unknown> {
  const res = await fetch(`${API_BASE}/api/schema`, { method: 'GET' });
  if (!res.ok) return null;
  return res.json().catch(() => null);
}

export interface KnowledgeHistoryItem {
  name: string;
  date: string;
}

export async function fetchKnowledgeHistory(): Promise<KnowledgeHistoryItem[]> {
  const res = await fetch(`${API_BASE}/api/knowledge/history`, { method: 'GET' });
  if (!res.ok) return [];
  const data = await res.json().catch(() => []);
  return Array.isArray(data) ? data : [];
}

export { API_BASE };
