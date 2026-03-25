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

  useEffect(() => {
    api.status().then(setStats).catch(() => {})
    const interval = setInterval(() => api.status().then(setStats).catch(() => {}), 10000)
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

      {stats && (
        <div className="ml-auto flex gap-5 text-xs" style={{ color: 'var(--text-muted)' }}>
          <span>{stats.graph?.nodes ?? 0} nodes</span>
          <span>{stats.graph?.edges ?? 0} edges</span>
          <span>{stats.agents?.active ?? 0} agents</span>
        </div>
      )}
    </nav>
  )
}
