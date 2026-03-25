import { useState } from 'react'
import type { LearnSession } from '../../hooks/useLearn'

interface GrowthChartProps {
  sessions: LearnSession[]
}

interface TooltipState {
  x: number
  y: number
  entities: number
  edges: number
  index: number
}

const W = 300
const H = 120
const PAD = { top: 12, right: 12, bottom: 24, left: 32 }
const INNER_W = W - PAD.left - PAD.right
const INNER_H = H - PAD.top - PAD.bottom

function buildCumulative(sessions: LearnSession[]) {
  const sorted = [...sessions].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
  let cumEntities = 0
  let cumEdges = 0
  return sorted.map(s => {
    cumEntities += s.entities_created ?? 0
    cumEdges += s.edges_created ?? 0
    return { entities: cumEntities, edges: cumEdges, date: s.created_at }
  })
}

function polyline(points: { x: number; y: number }[]) {
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
}

export function GrowthChart({ sessions }: GrowthChartProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)

  if (sessions.length < 2) {
    return (
      <div
        className="glass-panel"
        style={{ width: W, padding: '12px 16px', textAlign: 'center' }}
      >
        <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px' }}>Growth</div>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Need 2+ sessions</div>
      </div>
    )
  }

  const data = buildCumulative(sessions)
  const maxEntities = Math.max(...data.map(d => d.entities), 1)
  const maxEdges = Math.max(...data.map(d => d.edges), 1)
  const maxY = Math.max(maxEntities, maxEdges)

  const toX = (i: number) => PAD.left + (i / (data.length - 1)) * INNER_W
  const toY = (val: number) => PAD.top + INNER_H - (val / maxY) * INNER_H

  const entityPoints = data.map((d, i) => ({ x: toX(i), y: toY(d.entities) }))
  const edgePoints = data.map((d, i) => ({ x: toX(i), y: toY(d.edges) }))

  return (
    <div className="glass-panel" style={{ width: W, padding: '12px 16px', position: 'relative' }}>
      <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>Growth</span>
        <span style={{ display: 'flex', gap: '10px' }}>
          <span style={{ color: 'var(--accent-purple)' }}>● Entities</span>
          <span style={{ color: 'var(--accent-bright-blue)' }}>● Edges</span>
        </span>
      </div>

      <svg width={W} height={H} style={{ display: 'block', overflow: 'visible' }}>
        <defs>
          <filter id="glow-entity">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
          <filter id="glow-edge">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* Y axis ticks */}
        {[0, 0.5, 1].map(ratio => {
          const y = PAD.top + INNER_H - ratio * INNER_H
          return (
            <g key={ratio}>
              <line x1={PAD.left} y1={y} x2={W - PAD.right} y2={y} stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
              <text x={PAD.left - 4} y={y + 4} textAnchor="end" fontSize="8" fill="rgba(230,237,243,0.35)">
                {Math.round(maxY * ratio)}
              </text>
            </g>
          )
        })}

        {/* Edge line */}
        <path
          d={polyline(edgePoints)}
          fill="none"
          stroke="var(--accent-bright-blue)"
          strokeWidth="1.5"
          strokeOpacity="0.6"
          filter="url(#glow-edge)"
        />

        {/* Entity line */}
        <path
          d={polyline(entityPoints)}
          fill="none"
          stroke="var(--accent-purple)"
          strokeWidth="1.5"
          filter="url(#glow-entity)"
        />

        {/* Dots */}
        {entityPoints.map((pt, i) => (
          <circle
            key={`e-${i}`}
            cx={pt.x}
            cy={pt.y}
            r={3}
            fill="var(--accent-purple)"
            style={{ cursor: 'pointer', filter: 'url(#glow-entity)' }}
            onMouseEnter={() => setTooltip({ x: pt.x, y: pt.y, entities: data[i].entities, edges: data[i].edges, index: i })}
            onMouseLeave={() => setTooltip(null)}
          />
        ))}
        {edgePoints.map((pt, i) => (
          <circle
            key={`d-${i}`}
            cx={pt.x}
            cy={pt.y}
            r={3}
            fill="var(--accent-bright-blue)"
            strokeOpacity="0.6"
            style={{ cursor: 'pointer' }}
            onMouseEnter={() => setTooltip({ x: pt.x, y: pt.y, entities: data[i].entities, edges: data[i].edges, index: i })}
            onMouseLeave={() => setTooltip(null)}
          />
        ))}

        {/* X axis labels */}
        {data.map((_d, i) => {
          if (data.length > 6 && i % Math.ceil(data.length / 6) !== 0 && i !== data.length - 1) return null
          return (
            <text key={i} x={toX(i)} y={H - 4} textAnchor="middle" fontSize="8" fill="rgba(230,237,243,0.35)">
              {i + 1}
            </text>
          )
        })}
      </svg>

      {/* Tooltip */}
      {tooltip && (
        <div
          style={{
            position: 'absolute',
            left: tooltip.x + PAD.left > W / 2 ? undefined : tooltip.x + 8,
            right: tooltip.x + PAD.left > W / 2 ? W - tooltip.x + 8 : undefined,
            top: tooltip.y - 10,
            background: 'rgba(13, 17, 23, 0.95)',
            border: '1px solid var(--border)',
            borderRadius: '6px',
            padding: '6px 10px',
            pointerEvents: 'none',
            zIndex: 10,
            fontSize: '11px',
            whiteSpace: 'nowrap',
          }}
        >
          <div style={{ color: 'var(--accent-purple)' }}>Entities: {tooltip.entities}</div>
          <div style={{ color: 'var(--accent-bright-blue)' }}>Edges: {tooltip.edges}</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '9px', marginTop: '2px' }}>Session {tooltip.index + 1}</div>
        </div>
      )}
    </div>
  )
}
