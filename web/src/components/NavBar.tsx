import { useEffect, useState } from 'react'
import { api } from '../api/client'

type Tab = 'graph' | 'agents' | 'ask' | 'learn' | 'observe'

const tabs: { id: Tab; label: string }[] = [
  { id: 'graph', label: 'GRAPH' },
  { id: 'agents', label: 'AGENTS' },
  { id: 'ask', label: 'ASK' },
  { id: 'learn', label: 'LEARN' },
  { id: 'observe', label: 'OBSERVE' },
]

export function NavBar({ activeTab, onTabChange }: { activeTab: Tab; onTabChange: (t: Tab) => void }) {
  const [stats, setStats] = useState<any>(null)
  const [claudeOk, setClaudeOk] = useState<boolean | null>(null)
  const [claudeError, setClaudeError] = useState<string | null>(null)
  const [showClaudeDetail, setShowClaudeDetail] = useState(false)

  useEffect(() => {
    api.status().then(setStats).catch(() => {})
    api.claudeHealth().then(r => { setClaudeOk(r.available); setClaudeError(r.error || null) }).catch(() => setClaudeOk(false))
    const interval = setInterval(() => {
      api.status().then(setStats).catch(() => {})
      api.claudeHealth().then(r => { setClaudeOk(r.available); setClaudeError(r.error || null) }).catch(() => setClaudeOk(false))
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <nav className="flex items-center px-5 h-12 border-b" style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
      <div className="flex items-center gap-3 mr-8">
        <div className="w-2.5 h-2.5 rounded-full" style={{
          background: 'var(--accent-blue)',
          boxShadow: '0 0 12px var(--accent-blue), 0 0 24px rgba(88,166,255,0.3)',
          animation: 'pulse-glow 2s ease-in-out infinite',
        }} />
        <span className="text-sm font-semibold tracking-widest" style={{ color: 'var(--text-primary)' }}>
          MYCELIUM
        </span>
      </div>

      <div className="flex gap-6">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => onTabChange(t.id)}
            className={`text-xs tracking-wider pb-3 pt-3 border-b-2 transition-all ${
              activeTab === t.id ? 'tab-active' : 'border-transparent'
            }`}
            style={{ color: activeTab === t.id ? undefined : 'var(--text-muted)' }}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="ml-auto flex items-center gap-5 text-xs" style={{ color: 'var(--text-muted)' }}>
        {stats && (
          <>
            <span>{stats.graph?.nodes ?? 0} nodes</span>
            <span>{stats.graph?.edges ?? 0} edges</span>
            <span>{stats.agents?.active ?? 0} agents</span>
          </>
        )}

        {/* Claude CLI status */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setShowClaudeDetail(!showClaudeDetail)}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              background: 'none', border: '1px solid var(--border)',
              borderRadius: 6, padding: '3px 10px',
              cursor: 'pointer', fontFamily: 'inherit', fontSize: 11,
              color: claudeOk ? 'var(--accent-green)' : claudeOk === false ? '#f85149' : 'var(--text-muted)',
              transition: 'all 0.2s',
            }}
          >
            <div style={{
              width: 7, height: 7, borderRadius: '50%',
              background: claudeOk ? '#7ee787' : claudeOk === false ? '#f85149' : '#8b949e',
              boxShadow: claudeOk ? '0 0 8px rgba(126,231,135,0.6)' : claudeOk === false ? '0 0 8px rgba(248,81,73,0.6)' : 'none',
            }} />
            Claude
          </button>

          {showClaudeDetail && (
            <div className="glass-panel" style={{
              position: 'absolute', top: '100%', right: 0, marginTop: 8,
              padding: '12px 16px', minWidth: 220, zIndex: 100,
            }}>
              <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>
                Claude CLI Status
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <div style={{
                  width: 10, height: 10, borderRadius: '50%',
                  background: claudeOk ? '#7ee787' : '#f85149',
                  boxShadow: claudeOk ? '0 0 10px rgba(126,231,135,0.6)' : '0 0 10px rgba(248,81,73,0.6)',
                }} />
                <span style={{ fontSize: 12, color: claudeOk ? 'var(--accent-green)' : '#f85149' }}>
                  {claudeOk ? 'Connected' : 'Unavailable'}
                </span>
              </div>
              {claudeError && (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, wordBreak: 'break-word' }}>
                  {claudeError}
                </div>
              )}
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 8 }}>
                Used by Learn and Ask for LLM calls.
                {!claudeOk && ' Ask/Learn will fail until resolved.'}
              </div>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
