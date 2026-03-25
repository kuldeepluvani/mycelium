const BASE = ''

export async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) throw new Error(`${res.status}: ${res.statusText}`)
  return res.json()
}

export const api = {
  status: () => fetchJSON<any>('/api/status'),
  graphNodes: () => fetchJSON<{ nodes: any[] }>('/api/graph/nodes'),
  graphEdges: () => fetchJSON<{ edges: any[] }>('/api/graph/edges'),
  graphEntity: (id: string) => fetchJSON<any>(`/api/graph/entity/${id}`),
  graphDiff: (sessionId: string) => fetchJSON<any>(`/api/graph/diff?session_id=${sessionId}`),
  agents: () => fetchJSON<{ agents: any[] }>('/api/agents'),
  hierarchy: () => fetchJSON<{ meta_agents: any[] }>('/api/agents/hierarchy'),
  spillover: () => fetchJSON<any>('/api/agents/spillover'),
  pinAgent: (id: string, pinned: boolean) => fetchJSON<any>(`/api/agents/${id}/pin?pinned=${pinned}`, { method: 'PUT' }),
  renameAgent: (id: string, name: string) => fetchJSON<any>(`/api/agents/${id}/rename?name=${encodeURIComponent(name)}`, { method: 'PUT' }),
  retireAgent: (id: string) => fetchJSON<any>(`/api/agents/${id}/retire`, { method: 'PUT' }),
  ask: (query: string, mode = 'auto') => fetchJSON<any>('/api/ask', { method: 'POST', body: JSON.stringify({ query, mode }) }),
  askHistory: (limit = 20) => fetchJSON<any>(`/api/ask/history?limit=${limit}`),
  learnStart: (budget: number) => fetchJSON<any>(`/api/learn/start?budget=${budget}`, { method: 'POST' }),
  learnCancel: () => fetchJSON<any>('/api/learn/cancel', { method: 'POST' }),
  learnSessions: (limit = 20) => fetchJSON<any>(`/api/learn/sessions?limit=${limit}`),
  learnSession: (id: string) => fetchJSON<any>(`/api/learn/sessions/${id}`),
  observeEvents: (limit = 100) => fetchJSON<any>(`/api/observe/events?limit=${limit}`),
  observeHealth: () => fetchJSON<any>('/api/observe/health'),
}
