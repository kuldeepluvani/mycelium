import type { HealthMetric } from '../../hooks/useEvents'

interface HealthCardsProps {
  metrics: HealthMetric[]
}

function StatusDot({ status }: { status: string }) {
  const color =
    status === 'healthy' ? '#7ee787'
    : status === 'degraded' ? '#ffa657'
    : '#f85149'

  const glowColor =
    status === 'healthy' ? 'rgba(126,231,135,0.6)'
    : status === 'degraded' ? 'rgba(255,166,87,0.6)'
    : 'rgba(248,81,73,0.6)'

  return (
    <span
      style={{
        display: 'inline-block',
        width: 8,
        height: 8,
        borderRadius: '50%',
        background: color,
        boxShadow: `0 0 6px ${glowColor}`,
        flexShrink: 0,
        animation: status === 'healthy' ? 'pulse-glow 2s ease-in-out infinite' : undefined,
      }}
    />
  )
}

function formatLastCheck(ts?: string): string {
  if (!ts) return '—'
  try {
    const d = new Date(ts)
    if (isNaN(d.getTime())) return ts
    const secs = Math.floor((Date.now() - d.getTime()) / 1000)
    if (secs < 60) return `${secs}s ago`
    if (secs < 3600) return `${Math.floor(secs / 60)}m ago`
    return `${Math.floor(secs / 3600)}h ago`
  } catch {
    return ts
  }
}

function formatValue(v: number | string | undefined): string {
  if (v === undefined || v === null) return '—'
  if (typeof v === 'number') {
    return Number.isInteger(v) ? String(v) : v.toFixed(3)
  }
  return String(v)
}

export function HealthCards({ metrics }: HealthCardsProps) {
  if (metrics.length === 0) {
    return (
      <div
        className="glass-panel flex items-center justify-center px-6 py-4"
        style={{ minHeight: 80 }}
      >
        <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
          No health data yet — run a learn cycle
        </span>
      </div>
    )
  }

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: 12,
      }}
    >
      {metrics.map((m, idx) => {
        const statusColor =
          m.status === 'healthy' ? '#7ee787'
          : m.status === 'degraded' ? '#ffa657'
          : '#f85149'

        return (
          <div
            key={m.module ?? idx}
            className="glass-panel p-3 flex flex-col gap-1.5"
            style={{ borderLeft: `3px solid ${statusColor}44` }}
          >
            {/* Module name + status */}
            <div className="flex items-center gap-2 justify-between">
              <span
                className="text-xs font-semibold truncate"
                style={{ color: 'var(--text-primary)' }}
                title={m.module}
              >
                {m.module ?? 'unknown'}
              </span>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <StatusDot status={m.status} />
                <span className="text-xs" style={{ color: statusColor, textTransform: 'capitalize' }}>
                  {m.status}
                </span>
              </div>
            </div>

            {/* Metric */}
            {(m.metric_name || m.metric_value !== undefined) && (
              <div className="flex items-baseline gap-1.5">
                <span
                  className="text-base font-bold font-mono"
                  style={{ color: statusColor }}
                >
                  {formatValue(m.metric_value)}
                </span>
                {m.metric_name && (
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {m.metric_name}
                  </span>
                )}
              </div>
            )}

            {/* Last check */}
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
              Checked {formatLastCheck(m.last_check as string | undefined)}
            </div>
          </div>
        )
      })}
    </div>
  )
}
