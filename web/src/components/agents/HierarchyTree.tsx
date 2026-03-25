import { useState } from 'react'
import type { Agent, MetaAgent } from '../../hooks/useAgents'
import { AgentCard } from './AgentCard'

interface HierarchyTreeProps {
  agents: Agent[]
  metaAgents: MetaAgent[]
  onPin: (id: string, pinned: boolean) => Promise<void>
  onRename: (id: string, name: string) => Promise<void>
  onRetire: (id: string) => Promise<void>
}

interface MetaGroupProps {
  meta: MetaAgent
  children: Agent[]
  onPin: (id: string, pinned: boolean) => Promise<void>
  onRename: (id: string, name: string) => Promise<void>
  onRetire: (id: string) => Promise<void>
}

function MetaGroup({ meta, children, onPin, onRename, onRetire }: MetaGroupProps) {
  const [expanded, setExpanded] = useState(true)

  return (
    <div className="mb-6">
      {/* L2 Meta-agent header */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full text-left glass-panel p-4 mb-3 flex items-center justify-between transition-all"
        style={{
          cursor: 'pointer',
          borderLeft: '3px solid var(--accent-purple)',
          background: 'rgba(210,168,255,0.05)',
        }}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <span
              className="text-base font-semibold"
              style={{ color: 'var(--accent-purple)' }}
            >
              {meta.name}
            </span>
            {meta.domain && (
              <span
                className="text-xs px-2 py-0.5 rounded-full"
                style={{
                  background: 'rgba(210,168,255,0.12)',
                  color: 'var(--accent-purple)',
                  border: '1px solid rgba(210,168,255,0.25)',
                }}
              >
                {meta.domain}
              </span>
            )}
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{
                background: 'rgba(88,166,255,0.1)',
                color: 'var(--text-secondary)',
                border: '1px solid rgba(88,166,255,0.15)',
              }}
            >
              {children.length} agents
            </span>
          </div>
          {meta.description && (
            <div className="text-xs mt-1 truncate" style={{ color: 'var(--text-muted)' }}>
              {meta.description}
            </div>
          )}
        </div>
        <span
          className="text-sm ml-4 flex-shrink-0 transition-transform"
          style={{
            color: 'var(--text-muted)',
            transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s ease',
          }}
        >
          ▶
        </span>
      </button>

      {/* Connecting line + L1 children */}
      <div
        style={{
          maxHeight: expanded ? '9999px' : '0px',
          overflow: 'hidden',
          transition: 'max-height 0.35s ease',
        }}
      >
        <div className="relative pl-6">
          {/* Vertical connector line */}
          <div
            className="absolute left-2"
            style={{
              top: 0,
              bottom: children.length > 0 ? 20 : 0,
              width: 1,
              background: 'linear-gradient(to bottom, rgba(210,168,255,0.4), rgba(210,168,255,0.05))',
            }}
          />
          <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}>
            {children.map(agent => (
              <div key={agent.id} className="relative">
                {/* Horizontal connector */}
                <div
                  className="absolute"
                  style={{
                    left: -22,
                    top: '50%',
                    width: 20,
                    height: 1,
                    background: 'rgba(210,168,255,0.3)',
                  }}
                />
                <AgentCard
                  agent={agent}
                  onPin={onPin}
                  onRename={onRename}
                  onRetire={onRetire}
                />
              </div>
            ))}
            {children.length === 0 && (
              <div className="text-xs py-3" style={{ color: 'var(--text-muted)' }}>
                No child agents
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export function HierarchyTree({ agents, metaAgents, onPin, onRename, onRetire }: HierarchyTreeProps) {
  // Build a set of agent IDs that belong to a meta-agent group
  const assignedIds = new Set<string>()
  metaAgents.forEach(meta => {
    meta.children?.forEach(child => assignedIds.add(child.id))
  })

  // L1 agents not parented by any L2 in hierarchy response
  // Also check parent_id field from flat agents list
  const orphans = agents.filter(a => {
    if (assignedIds.has(a.id)) return false
    if (a.parent_id) return false
    return true
  })

  if (metaAgents.length === 0 && agents.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-lg mb-2" style={{ color: 'var(--text-secondary)' }}>No agents yet</div>
          <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Start a learn session to spawn agents
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      {/* L2 meta-agent groups */}
      {metaAgents.map(meta => (
        <MetaGroup
          key={meta.id}
          meta={meta}
          children={meta.children ?? []}
          onPin={onPin}
          onRename={onRename}
          onRetire={onRetire}
        />
      ))}

      {/* Orphan / unassigned L1 agents */}
      {orphans.length > 0 && (
        <div className="mb-6">
          <div
            className="glass-panel p-4 mb-3 flex items-center gap-3"
            style={{ borderLeft: '3px solid var(--text-muted)' }}
          >
            <span className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>
              Unassigned
            </span>
            <span
              className="text-xs px-2 py-0.5 rounded-full"
              style={{
                background: 'rgba(255,255,255,0.06)',
                color: 'var(--text-muted)',
                border: '1px solid rgba(255,255,255,0.1)',
              }}
            >
              {orphans.length} agents
            </span>
          </div>
          <div
            className="grid gap-3"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))' }}
          >
            {orphans.map(agent => (
              <AgentCard
                key={agent.id}
                agent={agent}
                onPin={onPin}
                onRename={onRename}
                onRetire={onRetire}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
