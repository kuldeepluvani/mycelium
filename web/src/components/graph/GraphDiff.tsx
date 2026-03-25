import { useState } from 'react'
import { api } from '../../api/client'

interface GraphDiffProps {
  sessions: Array<{ id: string; started_at: string; entities_created: number }>
  onDiffLoaded: (diff: { nodes: any[]; edges: any[] } | null) => void
}

export function GraphDiff({ sessions, onDiffLoaded }: GraphDiffProps) {
  const [selectedSession, setSelectedSession] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleToggle = async (sessionId: string) => {
    if (selectedSession === sessionId) {
      setSelectedSession(null)
      onDiffLoaded(null)
      return
    }
    setLoading(true)
    try {
      const diff = await api.graphDiff(sessionId)
      setSelectedSession(sessionId)
      onDiffLoaded(diff)
    } catch {
      onDiffLoaded(null)
    } finally {
      setLoading(false)
    }
  }

  if (sessions.length === 0) return null

  return (
    <div className="flex items-center gap-2">
      <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>Diff since:</span>
      <select
        value={selectedSession || ''}
        onChange={(e) => {
          if (e.target.value) {
            handleToggle(e.target.value)
          } else {
            setSelectedSession(null)
            onDiffLoaded(null)
          }
        }}
        className="text-xs px-2 py-1 rounded"
        style={{
          background: 'var(--bg-secondary)',
          color: 'var(--text-secondary)',
          border: '1px solid var(--border)',
        }}
        disabled={loading}
      >
        <option value="">None</option>
        {sessions.slice(0, 10).map(s => (
          <option key={s.id} value={s.id}>
            {new Date(s.started_at).toLocaleDateString()} (+{s.entities_created} entities)
          </option>
        ))}
      </select>
      {loading && <span style={{ color: 'var(--accent-blue)', fontSize: 11 }}>Loading...</span>}
    </div>
  )
}
