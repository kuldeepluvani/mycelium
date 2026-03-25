import { useState, useMemo } from 'react'
import type { MetaAgent, SpilloverData } from '../../hooks/useAgents'

interface SpilloverMapProps {
  metaAgents: MetaAgent[]
  spillover: SpilloverData
}

interface TooltipState {
  x: number
  y: number
  from: string
  to: string
  count: number
  details?: string
}

const SVG_SIZE = 500
const CENTER = SVG_SIZE / 2
const RADIUS = 170
const NODE_R = 28

function nodeColor(index: number): string {
  const palette = [
    '#d2a8ff', // purple
    '#58a6ff', // blue
    '#7ee787', // green
    '#ffa657', // orange
    '#f778ba', // pink
    '#79c0ff', // bright-blue
  ]
  return palette[index % palette.length]
}

function nodePos(i: number, total: number): { x: number; y: number } {
  const angle = (2 * Math.PI * i) / total - Math.PI / 2
  return {
    x: CENTER + RADIUS * Math.cos(angle),
    y: CENTER + RADIUS * Math.sin(angle),
  }
}

export function SpilloverMap({ metaAgents, spillover }: SpilloverMapProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)
  const [hoveredArc, setHoveredArc] = useState<string | null>(null)

  const nodes = metaAgents.slice(0, 12) // cap at 12 for readability
  const total = nodes.length

  // Build index map for O(1) lookup
  const indexMap = useMemo(() => {
    const map: Record<string, number> = {}
    nodes.forEach((n, i) => { map[n.id] = i })
    return map
  }, [nodes])

  // Aggregate spillover pairs
  const arcMap = useMemo(() => {
    const map: Record<string, { count: number; details?: string }> = {}
    for (const rel of spillover.relationships ?? []) {
      const a = rel.from_id < rel.to_id ? rel.from_id : rel.to_id
      const b = rel.from_id < rel.to_id ? rel.to_id : rel.from_id
      const key = `${a}|||${b}`
      if (!map[key]) map[key] = { count: 0, details: rel.details }
      map[key].count += rel.count ?? 1
    }
    return map
  }, [spillover])

  if (total === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-lg mb-2" style={{ color: 'var(--text-secondary)' }}>No meta-agents</div>
          <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Hierarchy must have L2 agents to show spillover map
          </div>
        </div>
      </div>
    )
  }

  // Quadratic bezier arc path between two nodes
  function arcPath(from: { x: number; y: number }, to: { x: number; y: number }): string {
    const mx = (from.x + to.x) / 2
    const my = (from.y + to.y) / 2
    // Pull control point toward center for curve
    const cx = mx + (CENTER - mx) * 0.4
    const cy = my + (CENTER - my) * 0.4
    return `M ${from.x} ${from.y} Q ${cx} ${cy} ${to.x} ${to.y}`
  }

  return (
    <div className="flex items-center justify-center h-full relative">
      <svg
        width={SVG_SIZE}
        height={SVG_SIZE}
        viewBox={`0 0 ${SVG_SIZE} ${SVG_SIZE}`}
        style={{ overflow: 'visible' }}
      >
        <defs>
          {nodes.map((node, i) => {
            const color = nodeColor(i)
            return (
              <radialGradient key={node.id} id={`glow-${node.id}`} cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor={color} stopOpacity="0.6" />
                <stop offset="100%" stopColor={color} stopOpacity="0" />
              </radialGradient>
            )
          })}
        </defs>

        {/* Arc connections */}
        {Object.entries(arcMap).map(([key, rel]) => {
          const [fromId, toId] = key.split('|||')
          const fi = indexMap[fromId]
          const ti = indexMap[toId]
          if (fi == null || ti == null) return null

          const fp = nodePos(fi, total)
          const tp = nodePos(ti, total)
          const isHovered = hoveredArc === key

          const maxCount = Math.max(...Object.values(arcMap).map(r => r.count), 1)
          const strokeW = 1 + (rel.count / maxCount) * 4

          const fromName = nodes[fi]?.name ?? fromId
          const toName = nodes[ti]?.name ?? toId

          return (
            <path
              key={key}
              d={arcPath(fp, tp)}
              fill="none"
              stroke={isHovered ? '#d2a8ff' : 'rgba(88,166,255,0.35)'}
              strokeWidth={isHovered ? strokeW + 1 : strokeW}
              style={{
                filter: isHovered ? 'drop-shadow(0 0 6px rgba(210,168,255,0.8))' : 'none',
                cursor: 'pointer',
                transition: 'stroke 0.2s, filter 0.2s',
              }}
              onMouseEnter={e => {
                setHoveredArc(key)
                setTooltip({
                  x: e.clientX,
                  y: e.clientY,
                  from: fromName,
                  to: toName,
                  count: rel.count,
                  details: rel.details,
                })
              }}
              onMouseMove={e => {
                setTooltip(prev => prev ? { ...prev, x: e.clientX, y: e.clientY } : null)
              }}
              onMouseLeave={() => {
                setHoveredArc(null)
                setTooltip(null)
              }}
            />
          )
        })}

        {/* Nodes */}
        {nodes.map((node, i) => {
          const pos = nodePos(i, total)
          const color = nodeColor(i)

          return (
            <g key={node.id}>
              {/* Glow halo */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={NODE_R + 10}
                fill={`url(#glow-${node.id})`}
                style={{ animation: 'pulse-glow 3s ease-in-out infinite' }}
              />
              {/* Node circle */}
              <circle
                cx={pos.x}
                cy={pos.y}
                r={NODE_R}
                fill="rgba(13,17,23,0.95)"
                stroke={color}
                strokeWidth={2}
                style={{
                  filter: `drop-shadow(0 0 8px ${color}66)`,
                }}
              />
              {/* Node label — name */}
              <text
                x={pos.x}
                y={pos.y - 5}
                textAnchor="middle"
                dominantBaseline="middle"
                fill={color}
                fontSize={9}
                fontWeight="600"
                fontFamily="Inter, sans-serif"
                style={{ pointerEvents: 'none' }}
              >
                {node.name.length > 12 ? node.name.slice(0, 11) + '…' : node.name}
              </text>
              {/* Child count */}
              <text
                x={pos.x}
                y={pos.y + 8}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="rgba(230,237,243,0.4)"
                fontSize={8}
                fontFamily="Inter, sans-serif"
                style={{ pointerEvents: 'none' }}
              >
                {node.children?.length ?? 0} agents
              </text>
            </g>
          )
        })}
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="glass-panel"
          style={{
            position: 'fixed',
            left: tooltip.x + 14,
            top: tooltip.y - 10,
            padding: '8px 12px',
            zIndex: 9999,
            pointerEvents: 'none',
            minWidth: 180,
          }}
        >
          <div className="text-xs font-semibold mb-1" style={{ color: 'var(--accent-purple)' }}>
            Spillover
          </div>
          <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            {tooltip.from} ↔ {tooltip.to}
          </div>
          <div className="text-xs mt-1" style={{ color: 'var(--accent-blue)' }}>
            {tooltip.count} relationship{tooltip.count !== 1 ? 's' : ''}
          </div>
          {tooltip.details && (
            <div className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
              {tooltip.details}
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      {Object.keys(arcMap).length === 0 && (
        <div
          className="absolute bottom-8 text-xs text-center"
          style={{ color: 'var(--text-muted)' }}
        >
          No spillover relationships yet
        </div>
      )}
    </div>
  )
}
