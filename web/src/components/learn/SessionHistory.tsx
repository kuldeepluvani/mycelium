import type { LearnSession } from '../../hooks/useLearn'

interface SessionHistoryProps {
  sessions: LearnSession[]
  selectedSession: LearnSession | null
  onSelectSession: (session: LearnSession | null) => void
  loading: boolean
}

function StatusBadge({ status }: { status: LearnSession['status'] }) {
  const config = {
    completed: { label: 'Completed', bg: 'rgba(126, 231, 135, 0.15)', color: '#7ee787', pulse: false },
    running: { label: 'Running', bg: 'rgba(88, 166, 255, 0.15)', color: '#58a6ff', pulse: true },
    interrupted: { label: 'Interrupted', bg: 'rgba(255, 166, 87, 0.15)', color: '#ffa657', pulse: false },
  }[status] ?? { label: status, bg: 'rgba(139, 148, 158, 0.15)', color: '#8b949e', pulse: false }

  return (
    <span
      className="badge"
      style={{
        background: config.bg,
        color: config.color,
        animation: config.pulse ? 'pulse-glow 1.5s ease-in-out infinite' : undefined,
      }}
    >
      {config.label}
    </span>
  )
}

function DetailPanel({ session }: { session: LearnSession }) {
  return (
    <div
      style={{
        padding: '16px',
        background: 'rgba(88, 166, 255, 0.04)',
        borderTop: '1px solid var(--border)',
        borderRadius: '0 0 10px 10px',
      }}
    >
      <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '12px' }}>
        Session Detail — {session.id}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '12px', marginBottom: '16px' }}>
        {[
          { label: 'Budget', value: session.budget },
          { label: 'Spent', value: session.spent },
          { label: 'Entities', value: session.entities_created },
          { label: 'Edges', value: session.edges_created },
          { label: 'Agents', value: session.agents_discovered ?? session.agents_spawned ?? 0 },
        ].map(({ label, value }) => (
          <div key={label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '18px', fontWeight: '700', color: 'var(--accent-blue)' }}>{value ?? '—'}</div>
            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>{label}</div>
          </div>
        ))}
      </div>

      {session.documents_processed && session.documents_processed.length > 0 && (
        <div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px' }}>Documents Processed</div>
          <div style={{ maxHeight: '120px', overflowY: 'auto' }}>
            {session.documents_processed.map((doc, i) => (
              <div
                key={i}
                style={{
                  fontSize: '11px',
                  color: 'var(--text-secondary)',
                  padding: '3px 0',
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
              >
                {doc}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export function SessionHistory({ sessions, selectedSession, onSelectSession, loading }: SessionHistoryProps) {
  if (loading && sessions.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '20px 24px' }}>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Loading sessions...</div>
      </div>
    )
  }

  if (!loading && sessions.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '20px 24px', textAlign: 'center' }}>
        <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>No learn sessions yet. Start a learn cycle above.</div>
      </div>
    )
  }

  const COLS = ['Status', 'Budget', 'Spent', 'Entities', 'Edges', 'Agents', 'Date']

  return (
    <div className="glass-panel" style={{ overflow: 'hidden' }}>
      <div style={{ padding: '14px 20px', borderBottom: '1px solid var(--border)' }}>
        <span style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Session History
        </span>
      </div>

      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {COLS.map(col => (
                <th
                  key={col}
                  style={{
                    padding: '8px 16px',
                    textAlign: 'left',
                    fontSize: '10px',
                    fontWeight: '600',
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.06em',
                    borderBottom: '1px solid var(--border)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sessions.map(session => {
              const isSelected = selectedSession?.id === session.id
              return (
                <>
                  <tr
                    key={session.id}
                    onClick={() => onSelectSession(isSelected ? null : session)}
                    style={{
                      cursor: 'pointer',
                      background: isSelected ? 'rgba(88, 166, 255, 0.07)' : 'transparent',
                      transition: 'background 0.15s ease',
                    }}
                    onMouseEnter={e => {
                      if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)'
                    }}
                    onMouseLeave={e => {
                      if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'transparent'
                    }}
                  >
                    <td style={{ padding: '10px 16px' }}>
                      <StatusBadge status={session.status} />
                    </td>
                    <td style={{ padding: '10px 16px', fontSize: '13px', color: 'var(--text-primary)' }}>{session.budget}</td>
                    <td style={{ padding: '10px 16px', fontSize: '13px', color: 'var(--text-secondary)' }}>{session.spent}</td>
                    <td style={{ padding: '10px 16px', fontSize: '13px', color: 'var(--accent-purple)' }}>{session.entities_created}</td>
                    <td style={{ padding: '10px 16px', fontSize: '13px', color: 'var(--accent-bright-blue)' }}>{session.edges_created}</td>
                    <td style={{ padding: '10px 16px', fontSize: '13px', color: 'var(--accent-green)' }}>{session.agents_discovered ?? session.agents_spawned ?? ''}</td>
                    <td style={{ padding: '10px 16px', fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {session.started_at ? new Date(session.started_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—'}
                    </td>
                  </tr>
                  {isSelected && (
                    <tr key={`${session.id}-detail`}>
                      <td colSpan={COLS.length} style={{ padding: 0 }}>
                        <DetailPanel session={session} />
                      </td>
                    </tr>
                  )}
                </>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
