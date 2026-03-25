import { useRef, type KeyboardEvent } from 'react'
import type { AskMode } from '../../hooks/useAsk'

interface QueryInputProps {
  query: string
  mode: AskMode
  loading: boolean
  onQueryChange: (q: string) => void
  onModeChange: (m: AskMode) => void
  onSubmit: () => void
}

const MODES: { label: string; value: AskMode }[] = [
  { label: 'Auto', value: 'auto' },
  { label: 'Cortex', value: 'cortex' },
  { label: 'Flat', value: 'flat' },
]

export function QueryInput({ query, mode, loading, onQueryChange, onModeChange, onSubmit }: QueryInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault()
      onSubmit()
    }
  }

  return (
    <div className="glass-panel p-4" style={{ borderColor: 'var(--border)' }}>
      {/* Mode toggle */}
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Mode</span>
        <div className="flex gap-1">
          {MODES.map(m => (
            <button
              key={m.value}
              onClick={() => onModeChange(m.value)}
              style={{
                padding: '3px 10px',
                borderRadius: '9999px',
                fontSize: '11px',
                fontWeight: 500,
                border: mode === m.value
                  ? '1px solid var(--accent-blue)'
                  : '1px solid var(--border)',
                background: mode === m.value
                  ? 'rgba(88, 166, 255, 0.15)'
                  : 'transparent',
                color: mode === m.value ? 'var(--accent-blue)' : 'var(--text-secondary)',
                cursor: 'pointer',
                boxShadow: mode === m.value ? '0 0 8px rgba(88, 166, 255, 0.3)' : 'none',
                transition: 'all 0.15s ease',
              }}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input row */}
      <div className="flex gap-3 items-end">
        <textarea
          ref={textareaRef}
          className="input-glow flex-1"
          value={query}
          onChange={e => onQueryChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask anything across the knowledge graph… (⌘+Enter to submit)"
          rows={3}
          disabled={loading}
          style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            padding: '10px 14px',
            color: 'var(--text-primary)',
            fontSize: '14px',
            resize: 'none',
            fontFamily: 'inherit',
            lineHeight: '1.5',
          }}
        />
        <button
          onClick={onSubmit}
          disabled={loading || !query.trim()}
          style={{
            padding: '10px 20px',
            borderRadius: '8px',
            border: '1px solid var(--accent-blue)',
            background: loading || !query.trim()
              ? 'rgba(88, 166, 255, 0.05)'
              : 'rgba(88, 166, 255, 0.15)',
            color: loading || !query.trim() ? 'var(--text-muted)' : 'var(--accent-blue)',
            cursor: loading || !query.trim() ? 'not-allowed' : 'pointer',
            fontSize: '13px',
            fontWeight: 500,
            whiteSpace: 'nowrap',
            boxShadow: loading || !query.trim() ? 'none' : '0 0 12px rgba(88, 166, 255, 0.4)',
            transition: 'all 0.2s ease',
            height: '78px',
          }}
        >
          {loading ? 'Thinking…' : 'Ask'}
        </button>
      </div>

      {/* Thinking indicator */}
      {loading && (
        <div
          className="mt-3 text-sm"
          style={{
            color: 'var(--accent-blue)',
            animation: 'pulse-glow 1.4s ease-in-out infinite',
          }}
        >
          ⬡ Routing query through agent network…
        </div>
      )}
    </div>
  )
}
