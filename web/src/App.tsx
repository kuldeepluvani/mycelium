import { useState, useEffect } from 'react'
import './styles/neural.css'
import { NavBar } from './components/NavBar'
import { wsManager } from './api/websocket'
import { api } from './api/client'
import { useGraph } from './hooks/useGraph'
import { ForceGraph } from './components/graph/ForceGraph'
import { NodeInspector } from './components/graph/NodeInspector'
import { GraphFilters } from './components/graph/GraphFilters'
import { useAgents } from './hooks/useAgents'
import { HierarchyTree } from './components/agents/HierarchyTree'
import { SpilloverMap } from './components/agents/SpilloverMap'
import { AskPage } from './components/ask/AskPage'
import { ObservePage } from './components/observe/ObservePage'
import { LearnPage } from './components/learn/LearnPage'

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
        {tab === 'graph' && <GraphExplorerPage />}
        {tab === 'agents' && <AgentsPage />}
        {tab === 'ask' && <AskPage />}
        {tab === 'learn' && <LearnPage />}
        {tab === 'observe' && <ObservePage />}
      </main>
    </div>
  )
}

function CoverageBar() {
  const [coverage, setCoverage] = useState<any>(null)
  useEffect(() => {
    api.coverage().then(setCoverage).catch(() => {})
  }, [])
  if (!coverage) return null
  const pct = coverage.coverage_pct || 0
  const barColor = pct > 70 ? 'var(--accent-green)' : pct > 30 ? 'var(--accent-blue)' : 'var(--accent-orange)'
  return (
    <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
          Knowledge Coverage
        </span>
        <span style={{ fontSize: 11, color: barColor, fontWeight: 600 }}>
          {pct}%
        </span>
      </div>
      <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`, background: barColor,
          boxShadow: `0 0 8px ${barColor}88`, borderRadius: 2,
          transition: 'width 0.8s ease',
        }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>
          {coverage.ingested_sources} / {coverage.total_sources} sources
        </span>
        <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>
          {coverage.entities} entities · {coverage.relationships} edges · {coverage.agents} agents
        </span>
      </div>
    </div>
  )
}

function GraphExplorerPage() {
  const graph = useGraph()

  return (
    <div
      style={{
        display: 'flex',
        height: '100%',
        overflow: 'hidden',
        background: 'var(--bg-primary)',
      }}
    >
      {/* Left: filters sidebar with coverage bar on top */}
      <div style={{ display: 'flex', flexDirection: 'column', width: 250, flexShrink: 0 }}>
        <CoverageBar />
      <GraphFilters
        nodes={graph.nodes}
        searchTerm={graph.searchTerm}
        setSearchTerm={graph.setSearchTerm}
        entityClassFilter={graph.entityClassFilter}
        toggleEntityClass={graph.toggleEntityClass}
        confidenceRange={graph.confidenceRange}
        setConfidenceRange={graph.setConfidenceRange}
      />
      </div>

      {/* Center: force graph */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        {graph.loading && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
              pointerEvents: 'none',
            }}
          >
            <div
              style={{
                color: 'var(--accent-blue)',
                fontSize: 14,
                textShadow: 'var(--glow-blue)',
                animation: 'pulse-glow 1.5s ease-in-out infinite',
              }}
            >
              Loading graph…
            </div>
          </div>
        )}
        {graph.error && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 10,
            }}
          >
            <div style={{ color: 'var(--accent-orange)', fontSize: 13 }}>
              {graph.error}
            </div>
          </div>
        )}
        {!graph.loading && (
          <ForceGraph
            nodes={graph.filteredNodes}
            edges={graph.filteredEdges}
            selectedNodeId={graph.selectedNode?.id ?? null}
            onSelectNode={graph.selectNode}
            agentMap={graph.agentMap}
          />
        )}
        {/* Node count badge */}
        <div
          style={{
            position: 'absolute',
            bottom: 12,
            left: 12,
            fontSize: 11,
            color: 'var(--text-muted)',
            background: 'rgba(0,0,0,0.5)',
            padding: '3px 8px',
            borderRadius: 6,
            backdropFilter: 'blur(8px)',
            pointerEvents: 'none',
          }}
        >
          {graph.filteredNodes.length} nodes · {graph.filteredEdges.length} edges
        </div>
      </div>

      {/* Right: node inspector (conditional) */}
      {graph.selectedNode && (
        <NodeInspector
          node={graph.selectedNode}
          onSelectNode={graph.selectNode}
          onClose={graph.deselectNode}
        />
      )}
    </div>
  )
}

function AgentsPage() {
  const {
    agents,
    metaAgents,
    spillover,
    loading,
    viewMode,
    setViewMode,
    pinAgent,
    renameAgent,
    retireAgent,
  } = useAgents()

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div
        className="flex items-center gap-3 px-6 py-3 border-b flex-shrink-0"
        style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}
      >
        <span className="text-xs font-semibold tracking-widest" style={{ color: 'var(--text-muted)' }}>
          VIEW
        </span>
        <div
          className="flex rounded overflow-hidden"
          style={{ border: '1px solid var(--border)' }}
        >
          <button
            onClick={() => setViewMode('tree')}
            className="text-xs px-3 py-1.5 transition-all"
            style={{
              background: viewMode === 'tree' ? 'rgba(88,166,255,0.15)' : 'transparent',
              color: viewMode === 'tree' ? 'var(--accent-blue)' : 'var(--text-muted)',
              borderRight: '1px solid var(--border)',
            }}
          >
            ⌥ Tree
          </button>
          <button
            onClick={() => setViewMode('spillover')}
            className="text-xs px-3 py-1.5 transition-all"
            style={{
              background: viewMode === 'spillover' ? 'rgba(210,168,255,0.15)' : 'transparent',
              color: viewMode === 'spillover' ? 'var(--accent-purple)' : 'var(--text-muted)',
            }}
          >
            ◎ Spillover
          </button>
        </div>

        {loading && (
          <span className="text-xs ml-auto" style={{ color: 'var(--text-muted)' }}>
            Loading...
          </span>
        )}
        {!loading && (
          <span className="text-xs ml-auto" style={{ color: 'var(--text-muted)' }}>
            {agents.length} agents · {metaAgents.length} meta-agents
          </span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {viewMode === 'tree' && (
          <HierarchyTree
            agents={agents}
            metaAgents={metaAgents}
            onPin={pinAgent}
            onRename={renameAgent}
            onRetire={retireAgent}
          />
        )}
        {viewMode === 'spillover' && (
          <SpilloverMap
            metaAgents={metaAgents}
            spillover={spillover}
          />
        )}
      </div>
    </div>
  )
}

