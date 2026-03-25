import { useState } from 'react'
import { getEntityColor, getEntityGlow } from '../../utils/colors'
import type { EntityDetail } from '../../hooks/useGraph'

interface NodeInspectorProps {
  node: EntityDetail
  onSelectNode: (id: string) => void
  onClose: () => void
}

export function NodeInspector({ node, onSelectNode, onClose }: NodeInspectorProps) {
  const [expandedRel, setExpandedRel] = useState<number | null>(null)
  const color = getEntityColor(node.entity_class)
  const glow = getEntityGlow(node.entity_class)

  return (
    <div
      className="glass-panel"
      style={{
        width: 350,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderRadius: 0,
        borderRight: 'none',
        borderTop: 'none',
        borderBottom: 'none',
        borderLeft: `2px solid ${color}`,
        boxShadow: `-4px 0 24px ${color}22`,
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '16px 16px 12px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 12,
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 18,
              fontWeight: 600,
              color: color,
              textShadow: glow,
              marginBottom: 6,
              wordBreak: 'break-word',
            }}
          >
            {node.name}
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <span
              className="badge"
              style={{
                background: `${color}22`,
                color: color,
                border: `1px solid ${color}44`,
              }}
            >
              {node.entity_class}
            </span>
            {node.domain && (
              <span
                className="badge"
                style={{
                  background: 'rgba(88,166,255,0.1)',
                  color: 'var(--text-secondary)',
                  border: '1px solid rgba(88,166,255,0.2)',
                }}
              >
                {node.domain}
              </span>
            )}
          </div>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: 18,
            lineHeight: 1,
            padding: 4,
            flexShrink: 0,
            transition: 'color 200ms',
          }}
          onMouseEnter={(e) => ((e.target as HTMLElement).style.color = 'var(--text-primary)')}
          onMouseLeave={(e) => ((e.target as HTMLElement).style.color = 'var(--text-muted)')}
        >
          ×
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {/* Confidence */}
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              fontSize: 11,
              color: 'var(--text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
              marginBottom: 6,
            }}
          >
            Confidence
          </div>
          <div
            style={{
              height: 6,
              background: 'rgba(255,255,255,0.08)',
              borderRadius: 3,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${Math.round(node.confidence * 100)}%`,
                background: color,
                boxShadow: `0 0 8px ${color}88`,
                borderRadius: 3,
                transition: 'width 600ms ease',
              }}
            />
          </div>
          <div
            style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}
          >
            {Math.round(node.confidence * 100)}%
          </div>
        </div>

        {/* Dates */}
        {(node.first_seen || node.last_seen) && (
          <div style={{ marginBottom: 16 }}>
            <Label>Timeline</Label>
            <div
              style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}
            >
              {node.first_seen && (
                <MetaItem label="First seen" value={formatDate(node.first_seen)} />
              )}
              {node.last_seen && (
                <MetaItem label="Last seen" value={formatDate(node.last_seen)} />
              )}
            </div>
          </div>
        )}

        {/* Provenance */}
        {node.provenance && node.provenance.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Label>Sources</Label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {node.provenance.map((src, i) => (
                <div
                  key={i}
                  style={{
                    fontSize: 11,
                    color: 'var(--text-secondary)',
                    background: 'rgba(88,166,255,0.05)',
                    border: '1px solid rgba(88,166,255,0.1)',
                    borderRadius: 6,
                    padding: '4px 8px',
                    fontFamily: 'monospace',
                    wordBreak: 'break-all',
                  }}
                >
                  {src}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Relationships */}
        {node.relationships && node.relationships.length > 0 && (
          <div>
            <Label>Relationships ({node.relationships.length})</Label>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {node.relationships.map((rel, i) => {
                const isExpanded = expandedRel === i
                return (
                  <div
                    key={i}
                    style={{
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid var(--border)',
                      borderRadius: 8,
                      overflow: 'hidden',
                      transition: 'border-color 200ms',
                    }}
                  >
                    <div
                      style={{
                        padding: '8px 10px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                      }}
                      onClick={() => setExpandedRel(isExpanded ? null : i)}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div
                          style={{
                            fontSize: 12,
                            color: 'var(--text-primary)',
                            fontWeight: 500,
                            whiteSpace: 'nowrap',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                          }}
                        >
                          {rel.target_name || rel.target_id}
                        </div>
                        <div
                          style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}
                        >
                          {rel.type}
                          {rel.category ? ` · ${rel.category}` : ''}
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <div
                          style={{
                            width: 32,
                            height: 4,
                            background: 'rgba(255,255,255,0.1)',
                            borderRadius: 2,
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              height: '100%',
                              width: `${Math.round(rel.confidence * 100)}%`,
                              background: color,
                            }}
                          />
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            onSelectNode(rel.target_id)
                          }}
                          style={{
                            background: `${color}22`,
                            border: `1px solid ${color}44`,
                            color: color,
                            borderRadius: 4,
                            padding: '2px 6px',
                            fontSize: 10,
                            cursor: 'pointer',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          Go →
                        </button>
                      </div>
                    </div>
                    {isExpanded && rel.rationale && (
                      <div
                        style={{
                          padding: '0 10px 10px',
                          fontSize: 11,
                          color: 'var(--text-secondary)',
                          lineHeight: 1.5,
                          borderTop: '1px solid var(--border)',
                          paddingTop: 8,
                        }}
                      >
                        {rel.rationale}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize: 11,
        color: 'var(--text-muted)',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        marginBottom: 8,
      }}
    >
      {children}
    </div>
  )
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid var(--border)',
        borderRadius: 6,
        padding: '6px 8px',
      }}
    >
      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>
        {label}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{value}</div>
    </div>
  )
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return iso
  }
}
