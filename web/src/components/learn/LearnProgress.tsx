import { useEffect, useRef } from 'react'
import type { LiveEvent, LearnProgress } from '../../hooks/useLearn'

interface LearnProgressProps {
  isLearning: boolean
  progress: LearnProgress
  liveEvents: LiveEvent[]
}

function EventRow({ event, index }: { event: LiveEvent; index: number }) {
  const getEventDisplay = (e: LiveEvent) => {
    switch (e.type) {
      case 'learn.started':
        return {
          icon: '◎',
          color: 'var(--accent-blue)',
          text: 'Learn cycle started',
          sub: e.budget ? `Budget: ${e.budget} calls` : undefined,
        }
      case 'learn.progress':
        return {
          icon: '→',
          color: 'var(--text-secondary)',
          text: `Used ${e.spent ?? 0} of ${e.budget ?? 0} calls`,
          sub: undefined,
        }
      case 'learn.document_processing':
        return {
          icon: '📄',
          color: 'var(--accent-bright-blue)',
          text: e.path ?? 'Processing document',
          sub: e.layer ? `Layer: ${e.layer}` : undefined,
        }
      case 'learn.entity_discovered':
        return {
          icon: '◆',
          color: 'var(--accent-purple)',
          text: e.entity ?? e.name ?? 'Entity discovered',
          sub: e.entity_type ?? undefined,
        }
      case 'learn.agent_spawned':
        return {
          icon: '⬡',
          color: 'var(--accent-green)',
          text: e.agent_name ?? e.name ?? 'Agent spawned',
          sub: e.domain ?? undefined,
        }
      case 'learn.complete':
        return {
          icon: '✓',
          color: 'var(--accent-green)',
          text: 'Learn cycle complete',
          sub: [
            e.entities_created != null && `${e.entities_created} entities`,
            e.edges_created != null && `${e.edges_created} edges`,
            e.agents_spawned != null && `${e.agents_spawned} agents`,
          ]
            .filter(Boolean)
            .join(' · ') || undefined,
        }
      default:
        return {
          icon: '·',
          color: 'var(--text-muted)',
          text: e.type,
          sub: undefined,
        }
    }
  }

  const display = getEventDisplay(event)
  const isComplete = event.type === 'learn.complete'
  const isAgentSpawned = event.type === 'learn.agent_spawned'

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        gap: '10px',
        padding: isComplete ? '8px 10px' : '6px 2px',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
        animation: 'slide-in-right 0.25s ease forwards',
        animationDelay: `${Math.min(index * 0.03, 0.3)}s`,
        opacity: 0,
        background: isComplete ? 'rgba(126, 231, 135, 0.04)' : 'transparent',
        borderRadius: isComplete ? '6px' : '0',
      }}
    >
      <span
        style={{
          color: display.color,
          fontSize: isAgentSpawned ? '14px' : '12px',
          flexShrink: 0,
          marginTop: '1px',
          animation: isAgentSpawned ? 'agent-flash 0.6s ease' : undefined,
        }}
      >
        {display.icon}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: '12px',
            color: isComplete ? display.color : 'var(--text-primary)',
            fontWeight: isComplete ? '600' : '400',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {display.text}
        </div>
        {display.sub && (
          <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '1px' }}>
            {display.sub}
          </div>
        )}
      </div>
      <span style={{ fontSize: '10px', color: 'var(--text-muted)', flexShrink: 0 }}>
        {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
      </span>
    </div>
  )
}

export function LearnProgress({ isLearning, progress, liveEvents }: LearnProgressProps) {
  const feedRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight
    }
  }, [liveEvents])

  if (!isLearning && liveEvents.length === 0) return null

  const ratio = progress.budget > 0 ? Math.min(progress.spent / progress.budget, 1) : 0
  const pct = Math.round(ratio * 100)

  return (
    <div className="glass-panel" style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      <style>{`
        @keyframes slide-in-right {
          from { opacity: 0; transform: translateX(16px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes progress-glow {
          0%, 100% { box-shadow: 0 0 8px rgba(88, 166, 255, 0.5); }
          50% { box-shadow: 0 0 18px rgba(88, 166, 255, 0.9); }
        }
        @keyframes agent-flash {
          0% { color: var(--accent-green); text-shadow: 0 0 12px rgba(126, 231, 135, 0.8); }
          100% { color: var(--accent-green); text-shadow: none; }
        }
      `}</style>

      {/* Progress bar */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)', fontWeight: '500' }}>
            {isLearning ? 'Learning...' : 'Complete'}
          </span>
          <span style={{ fontSize: '12px', color: 'var(--accent-blue)', fontWeight: '600' }}>
            {progress.spent} / {progress.budget} calls ({pct}%)
          </span>
        </div>
        <div
          style={{
            height: '6px',
            background: 'rgba(88, 166, 255, 0.1)',
            borderRadius: '3px',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${pct}%`,
              background: 'linear-gradient(90deg, rgba(88, 166, 255, 0.6), var(--accent-blue))',
              borderRadius: '3px',
              transition: 'width 0.4s ease',
              animation: isLearning ? 'progress-glow 2s ease-in-out infinite' : undefined,
            }}
          />
        </div>
      </div>

      {/* Event feed */}
      <div>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>
          Live Events
        </div>
        <div
          ref={feedRef}
          style={{
            maxHeight: '280px',
            overflowY: 'auto',
            paddingRight: '4px',
          }}
        >
          {liveEvents.map((event, i) => (
            <EventRow key={event.id} event={event} index={i} />
          ))}
          {isLearning && (
            <div style={{ display: 'flex', gap: '6px', padding: '8px 2px', alignItems: 'center' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)', animation: 'pulse-glow 1.5s ease-in-out infinite' }}>
                ● Waiting for events...
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
