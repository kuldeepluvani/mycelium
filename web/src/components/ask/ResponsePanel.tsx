import { useState } from 'react'
import type { AskResult } from '../../hooks/useAsk'

interface ResponsePanelProps {
  result: AskResult
  onFollowUp: (q: string) => void
}

// Colors cycled per agent
const AGENT_COLORS = [
  'var(--accent-blue)',
  'var(--accent-purple)',
  'var(--accent-green)',
  'var(--accent-orange)',
  'var(--accent-pink)',
  'var(--accent-bright-blue)',
]

export function ResponsePanel({ result, onFollowUp }: ResponsePanelProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* Main answer */}
      <div
        className="glass-panel p-5"
        style={{
          borderTop: '2px solid var(--accent-blue)',
          boxShadow: '0 0 20px rgba(88, 166, 255, 0.08)',
        }}
      >
        <div
          className="text-xs font-medium mb-3"
          style={{ color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}
        >
          Answer
        </div>
        <p className="text-sm leading-relaxed" style={{ color: result.answer ? 'var(--text-primary)' : 'var(--text-muted)' }}>
          {result.answer || 'Agents were activated but returned an empty response. This typically happens when Claude CLI (`claude -p`) returns empty output in the current environment. Try running `mycelium ask` from the terminal instead.'}
        </p>
      </div>

      {/* Agent responses (individual) */}
      {result.agents_used && result.agents_used.length > 0 && (
        <div className="glass-panel p-5">
          <div
            className="text-xs font-medium mb-3"
            style={{ color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}
          >
            Agent Responses
          </div>
          <div className="flex flex-col gap-2">
            {result.agents_used.map((agent, i) => (
              <AgentCard key={agent} name={agent} color={AGENT_COLORS[i % AGENT_COLORS.length]} />
            ))}
          </div>
        </div>
      )}

      {/* Rationale */}
      {result.rationale && (Array.isArray(result.rationale) ? result.rationale.length > 0 : !!result.rationale) && (
        <div className="glass-panel p-5">
          <div
            className="text-xs font-medium mb-3"
            style={{ color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}
          >
            Rationale
          </div>
          <ul className="text-sm space-y-1" style={{ color: 'var(--text-secondary)' }}>
            {(Array.isArray(result.rationale) ? result.rationale : String(result.rationale).split('\n').filter(Boolean)).map((line, i) => (
              <li key={i} className="flex gap-2">
                <span style={{ color: 'var(--accent-blue)', flexShrink: 0 }}>•</span>
                <span>{String(line).replace(/^[-•]\s*/, '')}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Knowledge Gaps */}
      {result.unknowns && result.unknowns.length > 0 && (
        <div
          className="glass-panel p-5"
          style={{ borderColor: 'rgba(255, 166, 87, 0.25)' }}
        >
          <div
            className="text-xs font-medium mb-3"
            style={{ color: 'var(--accent-orange)', letterSpacing: '0.08em', textTransform: 'uppercase' }}
          >
            Knowledge Gaps
          </div>
          <ul className="text-sm space-y-1" style={{ color: 'var(--text-secondary)' }}>
            {result.unknowns.map((u, i) => (
              <li key={i} className="flex gap-2">
                <span style={{ color: 'var(--accent-orange)', flexShrink: 0 }}>?</span>
                <span>{u}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Follow-ups */}
      {result.follow_ups && result.follow_ups.length > 0 && (
        <div className="glass-panel p-5">
          <div
            className="text-xs font-medium mb-3"
            style={{ color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}
          >
            Follow-up Questions
          </div>
          <div className="flex flex-col gap-2">
            {result.follow_ups.map((q, i) => (
              <button
                key={i}
                onClick={() => onFollowUp(q)}
                style={{
                  textAlign: 'left',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid var(--border)',
                  background: 'transparent',
                  color: 'var(--accent-blue)',
                  fontSize: '13px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={e => {
                  const el = e.currentTarget
                  el.style.background = 'rgba(88, 166, 255, 0.07)'
                  el.style.borderColor = 'rgba(88, 166, 255, 0.4)'
                  el.style.boxShadow = '0 0 8px rgba(88, 166, 255, 0.15)'
                }}
                onMouseLeave={e => {
                  const el = e.currentTarget
                  el.style.background = 'transparent'
                  el.style.borderColor = 'var(--border)'
                  el.style.boxShadow = 'none'
                }}
              >
                → {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function AgentCard({ name, color }: { name: string; color: string }) {
  const [open, setOpen] = useState(false)

  return (
    <div
      style={{
        border: '1px solid var(--border)',
        borderRadius: '8px',
        overflow: 'hidden',
        transition: 'border-color 0.15s ease',
      }}
    >
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 12px',
          background: open ? 'rgba(255,255,255,0.03)' : 'transparent',
          border: 'none',
          cursor: 'pointer',
          color: 'var(--text-primary)',
        }}
      >
        <div className="flex items-center gap-2">
          <div
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              background: color,
              boxShadow: `0 0 6px ${color}`,
            }}
          />
          <span className="text-sm font-medium" style={{ color }}>{name}</span>
        </div>
        <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div
          className="text-sm px-4 pb-3 pt-1"
          style={{ color: 'var(--text-secondary)', borderTop: '1px solid var(--border)' }}
        >
          No individual response data available.
        </div>
      )}
    </div>
  )
}
