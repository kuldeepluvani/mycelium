import { useState, useEffect } from 'react'
import type { RoutingStep } from '../../hooks/useAsk'

interface RoutingFlowProps {
  query: string
  steps: RoutingStep[]
  mode: string
}

const STEP_DELAYS = [0, 500, 1000, 1500] // ms after steps become available

export function RoutingFlow({ query, steps, mode }: RoutingFlowProps) {
  const [visibleStep, setVisibleStep] = useState(-1)

  useEffect(() => {
    if (steps.length === 0) {
      setVisibleStep(-1)
      return
    }

    setVisibleStep(0) // query card always first
    const timers: ReturnType<typeof setTimeout>[] = []

    steps.forEach((_, i) => {
      const delay = STEP_DELAYS[i] ?? (i * 400)
      const t = setTimeout(() => {
        setVisibleStep(i + 1) // +1 because 0 = query card
      }, delay + 100)
      timers.push(t)
    })

    return () => timers.forEach(clearTimeout)
  }, [steps])

  if (!query || steps.length === 0) return null

  // figure out which steps to show (filter l2 for flat mode)
  const displaySteps = mode === 'flat'
    ? steps.filter(s => s.type !== 'l2_routed')
    : steps

  return (
    <div className="glass-panel p-4" style={{ position: 'relative' }}>
      <div className="text-xs font-medium mb-4" style={{ color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
        Routing Flow
      </div>

      {/* Query card */}
      <FlowStep visible={visibleStep >= 0} delay={0}>
        <div
          style={{
            border: '1px solid var(--accent-blue)',
            borderRadius: '8px',
            padding: '10px 14px',
            background: 'rgba(88, 166, 255, 0.07)',
            boxShadow: '0 0 14px rgba(88, 166, 255, 0.2)',
          }}
        >
          <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Query</div>
          <div className="text-sm" style={{ color: 'var(--text-primary)' }}>{query}</div>
        </div>
      </FlowStep>

      {displaySteps.map((step, i) => {
        const stepVisible = visibleStep > i // show after query card (index 0)
        return (
          <div key={`${step.type}-${i}`}>
            {/* Connector line */}
            <ConnectorLine visible={stepVisible} />
            {/* Step card */}
            <FlowStep visible={stepVisible} delay={50}>
              <StepCard step={step} stepIndex={i} />
            </FlowStep>
          </div>
        )
      })}
    </div>
  )
}

function FlowStep({ visible, delay, children }: { visible: boolean; delay: number; children: React.ReactNode }) {
  return (
    <div
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(8px)',
        transition: `opacity 0.35s ease ${delay}ms, transform 0.35s ease ${delay}ms`,
      }}
    >
      {children}
    </div>
  )
}

function ConnectorLine({ visible }: { visible: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-start', paddingLeft: '24px', margin: '4px 0' }}>
      <div
        style={{
          width: '2px',
          height: '20px',
          background: visible
            ? 'linear-gradient(to bottom, rgba(88,166,255,0.6), rgba(88,166,255,0.2))'
            : 'transparent',
          borderRadius: '1px',
          transition: 'background 0.4s ease',
          boxShadow: visible ? '0 0 6px rgba(88,166,255,0.4)' : 'none',
        }}
      />
    </div>
  )
}

function StepCard({ step }: { step: RoutingStep; stepIndex?: number }) {
  switch (step.type) {
    case 'intent':
      return (
        <div
          style={{
            border: '1px solid rgba(126, 231, 135, 0.3)',
            borderRadius: '8px',
            padding: '10px 14px',
            background: 'rgba(126, 231, 135, 0.05)',
          }}
        >
          <div className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>Intent — Matched Entities</div>
          {step.entities && step.entities.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {step.entities.map((e, i) => (
                <EntityTag key={i} label={e} delay={i * 80} />
              ))}
            </div>
          ) : (
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>No specific entities matched</span>
          )}
        </div>
      )

    case 'l2_routed':
      return (
        <div
          style={{
            border: '1px solid rgba(210, 168, 255, 0.3)',
            borderRadius: '8px',
            padding: '10px 14px',
            background: 'rgba(210, 168, 255, 0.05)',
            boxShadow: '0 0 10px rgba(210, 168, 255, 0.1)',
          }}
        >
          <div className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>L2 Meta-Agent</div>
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium" style={{ color: 'var(--accent-purple)' }}>
              {step.meta}
            </span>
            {step.strategy && (
              <span className={`badge badge-${step.strategy}`}>
                {step.strategy}
              </span>
            )}
          </div>
        </div>
      )

    case 'l1_activated':
      return (
        <div
          style={{
            border: '1px solid rgba(88, 166, 255, 0.3)',
            borderRadius: '8px',
            padding: '10px 14px',
            background: 'rgba(88, 166, 255, 0.04)',
          }}
        >
          <div className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>L1 Agents Activated</div>
          {step.agents && step.agents.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {step.agents.map((agent, i) => (
                <AgentBadge key={i} name={agent} delay={i * 200} />
              ))}
            </div>
          ) : (
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>No agents activated</span>
          )}
        </div>
      )

    case 'synthesis':
      return (
        <div
          style={{
            border: '1px solid rgba(126, 231, 135, 0.4)',
            borderRadius: '8px',
            padding: '10px 14px',
            background: 'rgba(126, 231, 135, 0.06)',
            boxShadow: '0 0 14px rgba(126, 231, 135, 0.15)',
          }}
        >
          <div className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>Synthesis Complete</div>
          <div className="flex items-center gap-2">
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: 'var(--accent-green)',
                boxShadow: 'var(--glow-green)',
                animation: 'pulse-glow 1.5s ease-in-out infinite',
              }}
            />
            <span className="text-sm" style={{ color: 'var(--accent-green)' }}>Answer ready</span>
          </div>
        </div>
      )

    default:
      return null
  }
}

function EntityTag({ label, delay }: { label: string; delay: number }) {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), delay)
    return () => clearTimeout(t)
  }, [delay])
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '2px 10px',
        borderRadius: '9999px',
        fontSize: '11px',
        fontWeight: 500,
        border: '1px solid rgba(126, 231, 135, 0.4)',
        background: 'rgba(126, 231, 135, 0.1)',
        color: 'var(--accent-green)',
        opacity: visible ? 1 : 0,
        transform: visible ? 'scale(1)' : 'scale(0.85)',
        transition: 'all 0.25s ease',
        boxShadow: visible ? '0 0 6px rgba(126, 231, 135, 0.3)' : 'none',
      }}
    >
      {label}
    </span>
  )
}

function AgentBadge({ name, delay }: { name: string; delay: number }) {
  const [visible, setVisible] = useState(false)
  const [pulsing, setPulsing] = useState(false)

  useEffect(() => {
    const t1 = setTimeout(() => { setVisible(true); setPulsing(true) }, delay)
    const t2 = setTimeout(() => setPulsing(false), delay + 800)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [delay])

  return (
    <span
      className="badge badge-mature"
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'scale(1)' : 'scale(0.8)',
        transition: 'all 0.3s ease',
        boxShadow: pulsing ? 'var(--glow-blue)' : 'none',
        animation: pulsing ? 'pulse-glow 0.6s ease-in-out 2' : 'none',
      }}
    >
      {name}
    </span>
  )
}
