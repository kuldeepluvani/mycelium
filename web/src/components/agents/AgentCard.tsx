import { useState } from 'react'
import type { Agent } from '../../hooks/useAgents'

interface AgentCardProps {
  agent: Agent
  onPin: (id: string, pinned: boolean) => Promise<void>
  onRename: (id: string, name: string) => Promise<void>
  onRetire: (id: string) => Promise<void>
}

function confidenceColor(conf: number): string {
  if (conf >= 0.8) return 'var(--accent-green)'
  if (conf >= 0.5) return 'var(--accent-blue)'
  if (conf >= 0.3) return 'var(--accent-orange)'
  return 'var(--accent-pink)'
}

function domainBorderColor(domain?: string): string {
  if (!domain) return 'var(--accent-blue)'
  const d = domain.toLowerCase()
  if (d.includes('tech') || d.includes('engineer')) return 'var(--accent-blue)'
  if (d.includes('market') || d.includes('brand')) return 'var(--accent-purple)'
  if (d.includes('data') || d.includes('analyt')) return 'var(--accent-green)'
  if (d.includes('product')) return 'var(--accent-orange)'
  return 'var(--accent-bright-blue)'
}

export function AgentCard({ agent, onPin, onRename, onRetire }: AgentCardProps) {
  const [renaming, setRenaming] = useState(false)
  const [nameInput, setNameInput] = useState(agent.name)
  const [confirmRetire, setConfirmRetire] = useState(false)
  const [busy, setBusy] = useState(false)

  const conf = agent.confidence ?? 0
  const borderColor = domainBorderColor(agent.domain)

  async function handleRenameSubmit() {
    if (!nameInput.trim() || nameInput.trim() === agent.name) {
      setRenaming(false)
      return
    }
    setBusy(true)
    try {
      await onRename(agent.id, nameInput.trim())
    } finally {
      setBusy(false)
      setRenaming(false)
    }
  }

  async function handlePin() {
    setBusy(true)
    try {
      await onPin(agent.id, !agent.pinned)
    } finally {
      setBusy(false)
    }
  }

  async function handleRetire() {
    if (!confirmRetire) {
      setConfirmRetire(true)
      return
    }
    setBusy(true)
    try {
      await onRetire(agent.id)
    } finally {
      setBusy(false)
      setConfirmRetire(false)
    }
  }

  const statusClass = `badge badge-${agent.status}`

  return (
    <div
      className="glass-panel p-3 flex flex-col gap-2"
      style={{
        borderLeft: `3px solid ${borderColor}`,
        opacity: agent.status === 'retired' ? 0.6 : 1,
        transition: 'opacity 0.2s',
      }}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          {renaming ? (
            <input
              autoFocus
              value={nameInput}
              onChange={e => setNameInput(e.target.value)}
              onBlur={handleRenameSubmit}
              onKeyDown={e => {
                if (e.key === 'Enter') handleRenameSubmit()
                if (e.key === 'Escape') { setRenaming(false); setNameInput(agent.name) }
              }}
              disabled={busy}
              className="input-glow bg-transparent border rounded px-2 py-0.5 text-sm font-semibold w-full"
              style={{
                color: 'var(--text-primary)',
                borderColor: 'var(--accent-blue)',
              }}
            />
          ) : (
            <div className="flex items-center gap-2 min-w-0">
              {agent.pinned && (
                <span style={{ color: 'var(--accent-orange)', fontSize: 12 }}>📌</span>
              )}
              <span
                className="text-sm font-semibold truncate"
                style={{ color: 'var(--text-primary)' }}
              >
                {agent.name}
              </span>
            </div>
          )}
          {agent.domain && (
            <div className="text-xs truncate mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {agent.domain}
            </div>
          )}
        </div>
        <span className={statusClass}>{agent.status}</span>
      </div>

      {/* Confidence bar */}
      <div>
        <div className="flex justify-between mb-0.5">
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>confidence</span>
          <span className="text-xs" style={{ color: confidenceColor(conf) }}>
            {Math.round(conf * 100)}%
          </span>
        </div>
        <div
          className="rounded-full overflow-hidden"
          style={{ height: 3, background: 'rgba(255,255,255,0.08)' }}
        >
          <div
            className="h-full rounded-full"
            style={{
              width: `${conf * 100}%`,
              background: confidenceColor(conf),
              boxShadow: `0 0 6px ${confidenceColor(conf)}`,
              transition: 'width 0.4s ease',
            }}
          />
        </div>
      </div>

      {/* Entity count + key entities */}
      <div className="flex items-center gap-2 flex-wrap">
        {agent.entity_count != null && (
          <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            {agent.entity_count} entities
          </span>
        )}
        {agent.key_entities?.slice(0, 4).map(e => (
          <span
            key={e}
            className="text-xs px-1.5 py-0.5 rounded"
            style={{
              background: 'rgba(88,166,255,0.1)',
              color: 'var(--accent-bright-blue)',
              border: '1px solid rgba(88,166,255,0.2)',
            }}
          >
            {e}
          </span>
        ))}
      </div>

      {/* Knowledge gaps */}
      {agent.knowledge_gaps && agent.knowledge_gaps.length > 0 && (
        <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
          Gaps: {agent.knowledge_gaps.slice(0, 2).join(', ')}
          {agent.knowledge_gaps.length > 2 && ` +${agent.knowledge_gaps.length - 2}`}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 mt-1">
        {/* Pin button */}
        <button
          onClick={handlePin}
          disabled={busy}
          title={agent.pinned ? 'Unpin' : 'Pin'}
          className="text-xs px-2 py-1 rounded transition-all"
          style={{
            background: agent.pinned ? 'rgba(255,166,87,0.15)' : 'rgba(255,255,255,0.06)',
            color: agent.pinned ? 'var(--accent-orange)' : 'var(--text-muted)',
            border: `1px solid ${agent.pinned ? 'rgba(255,166,87,0.3)' : 'rgba(255,255,255,0.1)'}`,
            cursor: busy ? 'not-allowed' : 'pointer',
          }}
        >
          {agent.pinned ? '⊙ Unpin' : '◎ Pin'}
        </button>

        {/* Rename button */}
        {agent.status !== 'retired' && (
          <button
            onClick={() => { setRenaming(true); setNameInput(agent.name) }}
            disabled={busy || renaming}
            title="Rename"
            className="text-xs px-2 py-1 rounded transition-all"
            style={{
              background: 'rgba(255,255,255,0.06)',
              color: 'var(--text-muted)',
              border: '1px solid rgba(255,255,255,0.1)',
              cursor: busy ? 'not-allowed' : 'pointer',
            }}
          >
            ✎ Rename
          </button>
        )}

        {/* Retire button */}
        {agent.status !== 'retired' && (
          <button
            onClick={handleRetire}
            onBlur={() => setTimeout(() => setConfirmRetire(false), 200)}
            disabled={busy}
            title={confirmRetire ? 'Click again to confirm' : 'Retire agent'}
            className="text-xs px-2 py-1 rounded transition-all ml-auto"
            style={{
              background: confirmRetire ? 'rgba(247,120,186,0.2)' : 'rgba(255,255,255,0.04)',
              color: confirmRetire ? 'var(--accent-pink)' : 'var(--text-muted)',
              border: `1px solid ${confirmRetire ? 'rgba(247,120,186,0.4)' : 'rgba(255,255,255,0.08)'}`,
              cursor: busy ? 'not-allowed' : 'pointer',
            }}
          >
            {confirmRetire ? '⚠ Confirm?' : '✕ Retire'}
          </button>
        )}
      </div>
    </div>
  )
}
