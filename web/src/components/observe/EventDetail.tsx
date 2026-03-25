import type { MyceliumEvent } from '../../hooks/useEvents'
import { getEventCategory, CATEGORY_COLORS } from '../../hooks/useEvents'

interface EventDetailProps {
  event: MyceliumEvent
  onClose: () => void
}

function syntaxHighlight(json: string): string {
  return json
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(
      /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
      (match) => {
        if (/^"/.test(match)) {
          if (/:$/.test(match)) {
            // key
            return `<span style="color:#58a6ff">${match}</span>`
          } else {
            // string value
            return `<span style="color:#7ee787">${match}</span>`
          }
        } else if (/true|false/.test(match)) {
          return `<span style="color:#ffa657">${match}</span>`
        } else if (/null/.test(match)) {
          return `<span style="color:#f85149">${match}</span>`
        } else {
          // number
          return `<span style="color:#ffa657">${match}</span>`
        }
      }
    )
}

function formatTimestamp(ts?: string): string {
  if (!ts) return '—'
  try {
    return new Date(ts).toISOString()
  } catch {
    return ts
  }
}

export function EventDetail({ event, onClose }: EventDetailProps) {
  const cat = getEventCategory(event.event_type)
  const color = CATEGORY_COLORS[cat]

  const payloadJson = event.payload
    ? JSON.stringify(event.payload, null, 2)
    : JSON.stringify(
        Object.fromEntries(
          Object.entries(event).filter(([k]) => !['event_type', 'subject', 'module', 'timestamp', 'id'].includes(k))
        ),
        null,
        2
      )

  const highlighted = syntaxHighlight(payloadJson)

  return (
    <div
      className="glass-panel flex flex-col h-full"
      style={{
        width: 350,
        flexShrink: 0,
        borderLeft: `2px solid ${color}44`,
        borderRadius: '12px 0 0 12px',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        className="flex items-start justify-between p-4 flex-shrink-0"
        style={{ borderBottom: `1px solid ${color}33` }}
      >
        <div className="flex-1 min-w-0 pr-2">
          <div
            className="text-sm font-bold leading-tight"
            style={{ color, wordBreak: 'break-word' }}
          >
            {event.event_type}
          </div>
          <div className="text-xs mt-1 font-mono" style={{ color: 'var(--text-muted)' }}>
            {formatTimestamp(event.timestamp as string | undefined)}
          </div>
          {event.module && (
            <div className="mt-2">
              <span
                className="text-xs px-2 py-0.5 rounded"
                style={{
                  background: `${color}18`,
                  color,
                  border: `1px solid ${color}44`,
                  fontSize: 10,
                }}
              >
                {event.module as string}
              </span>
            </div>
          )}
          {event.subject && (
            <div className="text-xs mt-2" style={{ color: 'var(--text-secondary)' }}>
              {event.subject as string}
            </div>
          )}
        </div>
        <button
          onClick={onClose}
          className="flex-shrink-0 text-xs px-2 py-1 rounded transition-all"
          style={{
            background: 'rgba(255,255,255,0.06)',
            color: 'var(--text-muted)',
            border: '1px solid rgba(255,255,255,0.1)',
            cursor: 'pointer',
            lineHeight: 1,
          }}
          title="Close"
        >
          ✕
        </button>
      </div>

      {/* Payload */}
      <div className="flex-1 overflow-y-auto p-4" style={{ minHeight: 0 }}>
        <div className="text-xs font-medium mb-2" style={{ color: 'var(--text-muted)' }}>
          PAYLOAD
        </div>
        <pre
          className="text-xs font-mono leading-relaxed"
          style={{
            color: 'var(--text-secondary)',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
            margin: 0,
            padding: '12px',
            background: 'rgba(0,0,0,0.3)',
            borderRadius: 8,
            border: '1px solid rgba(255,255,255,0.06)',
          }}
          dangerouslySetInnerHTML={{ __html: highlighted }}
        />
      </div>
    </div>
  )
}
