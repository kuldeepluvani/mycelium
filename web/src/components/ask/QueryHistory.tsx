import type { HistoryItem, AskMode } from '../../hooks/useAsk'

interface QueryHistoryProps {
  history: HistoryItem[]
  onSelect: (item: HistoryItem) => void
}

const MODE_COLORS: Record<AskMode, string> = {
  auto: 'var(--accent-blue)',
  cortex: 'var(--accent-purple)',
  flat: 'var(--accent-green)',
}

function formatTime(ts: string): string {
  try {
    const d = new Date(ts)
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  } catch {
    return ''
  }
}

function truncate(text: string, max = 60): string {
  return text.length > max ? text.slice(0, max) + '…' : text
}

export function QueryHistory({ history, onSelect }: QueryHistoryProps) {
  return (
    <div
      style={{
        width: '250px',
        flexShrink: 0,
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: 'rgba(13, 17, 23, 0.6)',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 16px 10px',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div
          className="text-xs font-medium"
          style={{ color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}
        >
          Query History
        </div>
      </div>

      {/* List */}
      <div style={{ overflowY: 'auto', flex: 1 }}>
        {history.length === 0 ? (
          <div
            className="text-xs p-4"
            style={{ color: 'var(--text-muted)' }}
          >
            No queries yet. Ask something above.
          </div>
        ) : (
          history.map((item, i) => (
            <HistoryEntry key={i} item={item} onSelect={onSelect} />
          ))
        )}
      </div>
    </div>
  )
}

function HistoryEntry({ item, onSelect }: { item: HistoryItem; onSelect: (item: HistoryItem) => void }) {
  const modeColor = MODE_COLORS[item.mode] ?? 'var(--accent-blue)'
  const agentCount = item.result?.agents_used?.length ?? 0

  return (
    <button
      onClick={() => onSelect(item)}
      style={{
        width: '100%',
        textAlign: 'left',
        padding: '10px 16px',
        borderBottom: '1px solid rgba(88, 166, 255, 0.06)',
        background: 'transparent',
        border: 'none',
        borderBottomWidth: '1px',
        borderBottomStyle: 'solid',
        borderBottomColor: 'rgba(88, 166, 255, 0.06)',
        cursor: 'pointer',
        transition: 'background 0.15s ease',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.background = 'rgba(88, 166, 255, 0.07)'
        e.currentTarget.style.boxShadow = 'inset 2px 0 0 var(--accent-blue)'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.background = 'transparent'
        e.currentTarget.style.boxShadow = 'none'
      }}
    >
      {/* Query text */}
      <div
        className="text-xs mb-2"
        style={{
          color: 'var(--text-primary)',
          lineHeight: '1.4',
          fontWeight: 400,
        }}
      >
        {truncate(item.query)}
      </div>

      {/* Meta row */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Mode badge */}
        <span
          style={{
            padding: '1px 7px',
            borderRadius: '9999px',
            fontSize: '10px',
            fontWeight: 500,
            border: `1px solid ${modeColor}`,
            color: modeColor,
            background: `${modeColor}15`,
          }}
        >
          {item.mode}
        </span>

        {/* Agent count */}
        {agentCount > 0 && (
          <span
            style={{
              fontSize: '10px',
              color: 'var(--text-muted)',
            }}
          >
            {agentCount} agent{agentCount !== 1 ? 's' : ''}
          </span>
        )}

        {/* Timestamp */}
        {item.timestamp && (
          <span
            style={{
              fontSize: '10px',
              color: 'var(--text-muted)',
              marginLeft: 'auto',
            }}
          >
            {formatTime(item.timestamp)}
          </span>
        )}
      </div>
    </button>
  )
}
