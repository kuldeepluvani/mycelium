import { useState, useMemo, useEffect } from 'react'
import { getEntityColor } from '../../utils/colors'
import { api } from '../../api/client'
import type { GraphNode } from '../../hooks/useGraph'

interface GraphFiltersProps {
  nodes: GraphNode[]
  searchTerm: string
  setSearchTerm: (v: string) => void
  entityClassFilter: Set<string>
  toggleEntityClass: (cls: string) => void
  confidenceRange: [number, number]
  setConfidenceRange: (v: [number, number]) => void
}

export function GraphFilters({
  nodes,
  searchTerm,
  setSearchTerm,
  entityClassFilter,
  toggleEntityClass,
  confidenceRange,
  setConfidenceRange,
}: GraphFiltersProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [typesOpen, setTypesOpen] = useState(false)

  const classCounts = useMemo(() => {
    const counts = new Map<string, number>()
    nodes.forEach((n) => {
      counts.set(n.entity_class, (counts.get(n.entity_class) ?? 0) + 1)
    })
    return Array.from(counts.entries()).sort((a, b) => b[1] - a[1])
  }, [nodes])

  return (
    <div
      className="glass-panel"
      style={{
        width: collapsed ? 40 : 250,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 0,
        borderLeft: 'none',
        borderTop: 'none',
        borderBottom: 'none',
        transition: 'width 200ms ease',
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      {/* Toggle button */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        style={{
          alignSelf: collapsed ? 'center' : 'flex-end',
          background: 'none',
          border: 'none',
          color: 'var(--text-muted)',
          cursor: 'pointer',
          fontSize: 14,
          padding: '12px 10px 4px',
          transition: 'color 200ms',
        }}
        onMouseEnter={(e) => ((e.target as HTMLElement).style.color = 'var(--accent-blue)')}
        onMouseLeave={(e) => ((e.target as HTMLElement).style.color = 'var(--text-muted)')}
        title={collapsed ? 'Expand filters' : 'Collapse filters'}
      >
        {collapsed ? '▶' : '◀'}
      </button>

      {!collapsed && (
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '8px 14px 14px',
            display: 'flex',
            flexDirection: 'column',
            gap: 20,
          }}
        >
          <SectionLabel>Search</SectionLabel>
          {/* Search */}
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Filter by name..."
            className="input-glow"
            style={{
              width: '100%',
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '7px 10px',
              color: 'var(--text-primary)',
              fontSize: 13,
              boxSizing: 'border-box',
            }}
          />

          {/* Knowledge coverage */}
          <CoverageBar />

          {/* Entity classes */}
          <div>
            <button
              onClick={() => setTypesOpen(o => !o)}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                width: '100%', background: 'none', border: 'none', padding: 0,
                cursor: 'pointer', color: 'var(--text-muted)',
              }}
            >
              <SectionLabel>Entity Types ({classCounts.length})</SectionLabel>
              <span style={{ fontSize: 10, transition: 'transform 200ms', transform: typesOpen ? 'rotate(180deg)' : 'rotate(0)' }}>▼</span>
            </button>
            <div style={{
              display: 'flex', flexDirection: 'column', gap: 4, marginTop: 8,
              maxHeight: typesOpen ? '2000px' : '0px',
              overflow: 'hidden',
              transition: 'max-height 300ms ease',
            }}>
              {classCounts.map(([cls, count]) => {
                const color = getEntityColor(cls)
                const active = entityClassFilter.has(cls)
                return (
                  <label
                    key={cls}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                      cursor: 'pointer',
                      padding: '4px 6px',
                      borderRadius: 6,
                      background: active ? `${color}11` : 'transparent',
                      transition: 'background 200ms',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={active}
                      onChange={() => toggleEntityClass(cls)}
                      style={{ accentColor: color, width: 13, height: 13, cursor: 'pointer' }}
                    />
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: color,
                        boxShadow: `0 0 6px ${color}`,
                        flexShrink: 0,
                      }}
                    />
                    <span
                      style={{
                        fontSize: 12,
                        color: active ? 'var(--text-primary)' : 'var(--text-muted)',
                        flex: 1,
                        transition: 'color 200ms',
                      }}
                    >
                      {cls}
                    </span>
                    <span
                      style={{
                        fontSize: 11,
                        color: 'var(--text-muted)',
                        background: 'rgba(255,255,255,0.05)',
                        borderRadius: 9999,
                        padding: '1px 6px',
                      }}
                    >
                      {count}
                    </span>
                  </label>
                )
              })}
            </div>
          </div>

          {/* Confidence range */}
          <div>
            <SectionLabel>
              Confidence{' '}
              <span style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>
                {Math.round(confidenceRange[0] * 100)}% – {Math.round(confidenceRange[1] * 100)}%
              </span>
            </SectionLabel>
            <div style={{ marginTop: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <RangeRow
                label="Min"
                value={confidenceRange[0]}
                min={0}
                max={confidenceRange[1]}
                onChange={(v) => setConfidenceRange([v, confidenceRange[1]])}
              />
              <RangeRow
                label="Max"
                value={confidenceRange[1]}
                min={confidenceRange[0]}
                max={1}
                onChange={(v) => setConfidenceRange([confidenceRange[0], v])}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize: 11,
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        fontWeight: 600,
      }}
    >
      {children}
    </div>
  )
}

function RangeRow({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  onChange: (v: number) => void
}) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span style={{ fontSize: 11, color: 'var(--text-muted)', width: 24 }}>{label}</span>
      <input
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={value}
        onChange={(e) => {
          const v = parseFloat(e.target.value)
          if (v >= min && v <= max) onChange(v)
        }}
        style={{ flex: 1, accentColor: 'var(--accent-blue)', cursor: 'pointer' }}
      />
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
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
        <SectionLabel>Coverage</SectionLabel>
        <span style={{ fontSize: 11, color: barColor, fontWeight: 600 }}>{pct}%</span>
      </div>
      <div style={{ height: 4, background: 'rgba(255,255,255,0.06)', borderRadius: 2, overflow: 'hidden' }}>
        <div style={{
          height: '100%', width: `${pct}%`, background: barColor,
          boxShadow: `0 0 8px ${barColor}88`, borderRadius: 2,
          transition: 'width 0.8s ease',
        }} />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>{coverage.ingested_sources}/{coverage.total_sources} sources</span>
        <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>{coverage.entities} entities</span>
      </div>
    </div>
  )
}
