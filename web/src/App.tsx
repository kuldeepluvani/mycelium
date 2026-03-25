import { useState, useEffect } from 'react'
import './styles/neural.css'
import { NavBar } from './components/NavBar'
import { wsManager } from './api/websocket'

type Tab = 'graph' | 'agents' | 'ask' | 'learn' | 'observe'

export default function App() {
  const [tab, setTab] = useState<Tab>('graph')

  useEffect(() => {
    wsManager.connect()
    return () => wsManager.disconnect()
  }, [])

  return (
    <div className="h-screen flex flex-col" style={{ background: 'var(--bg-primary)' }}>
      <NavBar activeTab={tab} onTabChange={setTab} />
      <main className="flex-1 overflow-hidden">
        {tab === 'graph' && <Placeholder label="Graph Explorer" />}
        {tab === 'agents' && <Placeholder label="Agent Hierarchy" />}
        {tab === 'ask' && <Placeholder label="Ask Interface" />}
        {tab === 'learn' && <Placeholder label="Learn Dashboard" />}
        {tab === 'observe' && <Placeholder label="Observe Events" />}
      </main>
    </div>
  )
}

function Placeholder({ label }: { label: string }) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="text-center">
        <div className="text-2xl font-light mb-2" style={{ color: 'var(--text-secondary)' }}>{label}</div>
        <div className="text-sm" style={{ color: 'var(--text-muted)' }}>Coming next</div>
      </div>
    </div>
  )
}
