import { useRef, useEffect } from 'react'
import type { MyceliumEvent, EventCategory } from '../../hooks/useEvents'
import { getEventCategory, CATEGORY_COLORS } from '../../hooks/useEvents'

interface EventStreamProps {
  events: MyceliumEvent[]
  filters: Set<EventCategory>
  onToggleFilter: (category: EventCategory) => void
  selectedEvent: MyceliumEvent | null
  onSelectEvent: (event: MyceliumEvent) => void
}

const ALL_CATEGORIES: EventCategory[] = ['perception', 'network', 'serve', 'orchestrator', 'system']

const CATEGORY_LABELS: Record<EventCategory, string> = {
  perception: 'Perception',
  network: 'Network',
  serve: 'Serve',
  orchestrator: 'Orchestrator',
  system: 'System',
}

function relativeTime(ts?: string): string {
  if (!ts) return '—'
  const d = new Date(ts)
  if (isNaN(d.getTime())) return ts
  const secs = Math.floor((Date.now() - d.getTime()) / 1000)
  if (secs < 5) return 'just now'
  if (secs < 60) return `${secs}s ago`
  if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
  if (secs < 86400) return `${Math.floor(secs / 3600)}h ago`
  return `${Math.floor(secs / 86400)}d ago`
}

function truncate(s?: string, max = 40): string {
  if (!s) return '—'
  return s.length > max ? s.slice(0, max) + '…' : s
}

export function EventStream({
  events,
  filters,
  onToggleFilter,
  selectedEvent,
  onSelectEvent,
}: EventStreamProps) {
  const listRef = useRef<HTMLDivElement>(null)

  // Scroll to top when new events arrive (newest first)
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = 0
    }
  }, [events.length])

  return (
    <div className="flex flex-col h-full">
      {/* Filter toggles */}
      <div className="flex items-center gap-2 px-4 py-3 flex-shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
        <span className="text-xs font-medium mr-1" style={{ color: 'var(--text-muted)' }}>Filter:</span>
        {ALL_CATEGORIES.map(cat => {
          const active = filters.has(cat)
          const color = CATEGORY_COLORS[cat]
          return (
            <button
              key={cat}
              onClick={() => onToggleFilter(cat)}
              className="text-xs px-3 py-1 rounded-full transition-all"
              style={{
                background: active ? `${color}22` : 'rgba(255,255,255,0.04)',
                color: active ? color : 'var(--text-muted)',
                border: `1px solid ${active ? color + '66' : 'rgba(255,255,255,0.1)'}`,
                cursor: 'pointer',
                fontWeight: active ? 600 : 400,
                boxShadow: active ? `0 0 8px ${color}33` : 'none',
                transition: 'all 0.15s ease',
              }}
            >
              {CATEGORY_LABELS[cat]}
            </button>
          )
        })}
        <span className="ml-auto text-xs" style={{ color: 'var(--text-muted)' }}>
          {events.length} events
        </span>
      </div>

      {/* Event list */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto"
        style={{ minHeight: 0 }}
      >
        {events.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
              No events yet — waiting for activity...
            </span>
          </div>
        ) : (
          events.map((event, idx) => {
            const cat = getEventCategory(event.event_type)
            const color = CATEGORY_COLORS[cat]
            const isSelected = selectedEvent === event
            const key = event.id ?? `${event.event_type}-${idx}`

            return (
              <div
                key={key}
                onClick={() => onSelectEvent(event)}
                className="event-row"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: '8px 16px',
                  borderLeft: `3px solid ${color}`,
                  borderBottom: '1px solid rgba(255,255,255,0.04)',
                  cursor: 'pointer',
                  background: isSelected
                    ? `${color}11`
                    : 'transparent',
                  transition: 'background 0.15s ease',
                  animation: idx === 0 ? 'event-slide-in 0.25s ease both' : undefined,
                }}
                onMouseEnter={e => {
                  if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.03)'
                }}
                onMouseLeave={e => {
                  if (!isSelected) (e.currentTarget as HTMLElement).style.background = 'transparent'
                }}
              >
                {/* Timestamp */}
                <span
                  className="text-xs font-mono flex-shrink-0"
                  style={{ color: 'var(--text-muted)', width: 70, textAlign: 'right' }}
                >
                  {relativeTime(event.timestamp as string | undefined)}
                </span>

                {/* Event type */}
                <span
                  className="text-xs font-semibold flex-shrink-0"
                  style={{ color, width: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                  title={event.event_type}
                >
                  {event.event_type}
                </span>

                {/* Subject */}
                <span
                  className="text-xs flex-1 truncate"
                  style={{ color: 'var(--text-secondary)' }}
                  title={event.subject as string | undefined}
                >
                  {truncate(event.subject as string | undefined)}
                </span>

                {/* Module badge */}
                {event.module && (
                  <span
                    className="text-xs px-2 py-0.5 rounded flex-shrink-0"
                    style={{
                      background: `${color}18`,
                      color,
                      border: `1px solid ${color}44`,
                      fontSize: 10,
                    }}
                  >
                    {event.module as string}
                  </span>
                )}
              </div>
            )
          })
        )}
      </div>

      <style>{`
        @keyframes event-slide-in {
          from { opacity: 0; transform: translateX(20px); }
          to   { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </div>
  )
}
