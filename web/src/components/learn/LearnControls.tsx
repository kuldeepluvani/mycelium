import { useState } from 'react'

interface LearnControlsProps {
  isLearning: boolean
  onStart: (budget: number) => void
}

interface PresetConfig {
  label: string
  budget: number
  size: 'small' | 'medium' | 'large'
  description: string
  variant: 'outline' | 'filled' | 'glow'
}

const PRESETS: PresetConfig[] = [
  { label: 'Quick', budget: 20, size: 'small', description: 'Fast shallow scan', variant: 'outline' },
  { label: 'Standard', budget: 50, size: 'medium', description: 'Balanced exploration', variant: 'filled' },
  { label: 'Deep', budget: 100, size: 'large', description: 'Full deep dive', variant: 'glow' },
]

function PresetButton({
  config,
  disabled,
  onClick,
}: {
  config: PresetConfig
  disabled: boolean
  onClick: () => void
}) {
  const sizeStyles: Record<string, React.CSSProperties> = {
    small: { padding: '12px 20px', minWidth: '100px' },
    medium: { padding: '16px 28px', minWidth: '120px' },
    large: { padding: '20px 36px', minWidth: '140px' },
  }

  const variantStyles: Record<string, React.CSSProperties> = {
    outline: {
      background: 'transparent',
      border: '1px solid var(--accent-blue)',
      color: 'var(--accent-blue)',
    },
    filled: {
      background: 'rgba(88, 166, 255, 0.2)',
      border: '1px solid var(--accent-blue)',
      color: 'var(--accent-blue)',
    },
    glow: {
      background: 'rgba(88, 166, 255, 0.25)',
      border: '1px solid var(--accent-blue)',
      color: 'var(--accent-blue)',
      boxShadow: '0 0 20px rgba(88, 166, 255, 0.4), inset 0 0 20px rgba(88, 166, 255, 0.05)',
    },
  }

  const disabledStyle: React.CSSProperties = disabled
    ? { opacity: 0.35, cursor: 'not-allowed', pointerEvents: 'none' }
    : { cursor: 'pointer' }

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        ...sizeStyles[config.size],
        ...variantStyles[config.variant],
        ...disabledStyle,
        borderRadius: '10px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: '6px',
        transition: 'all 0.2s ease',
        fontFamily: 'inherit',
      }}
      onMouseEnter={e => {
        if (!disabled) {
          const el = e.currentTarget
          el.style.transform = 'translateY(-2px)'
          el.style.boxShadow = '0 0 24px rgba(88, 166, 255, 0.5)'
        }
      }}
      onMouseLeave={e => {
        const el = e.currentTarget
        el.style.transform = 'translateY(0)'
        el.style.boxShadow = config.variant === 'glow'
          ? '0 0 20px rgba(88, 166, 255, 0.4), inset 0 0 20px rgba(88, 166, 255, 0.05)'
          : ''
      }}
    >
      <span style={{ fontSize: '22px', fontWeight: '700', letterSpacing: '-0.5px' }}>
        {config.budget}
      </span>
      <span style={{ fontSize: '11px', fontWeight: '600', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
        {config.label}
      </span>
      <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: '400' }}>
        {config.description}
      </span>
    </button>
  )
}

export function LearnControls({ isLearning, onStart }: LearnControlsProps) {
  const [customBudget, setCustomBudget] = useState<string>('30')

  const handleCustomStart = () => {
    const b = parseInt(customBudget, 10)
    if (!isNaN(b) && b > 0) onStart(b)
  }

  return (
    <div className="glass-panel" style={{ padding: '20px 24px' }}>
      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '4px' }}>
          Learn Cycle
        </div>
        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
          {isLearning ? 'Learning in progress...' : 'Select a budget to start a new learn cycle'}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '14px', alignItems: 'flex-end', flexWrap: 'wrap' }}>
        {PRESETS.map(preset => (
          <PresetButton
            key={preset.label}
            config={preset}
            disabled={isLearning}
            onClick={() => onStart(preset.budget)}
          />
        ))}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginLeft: '8px' }}>
          <label style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Custom
          </label>
          <div style={{ display: 'flex', gap: '6px' }}>
            <input
              type="number"
              min="1"
              max="500"
              value={customBudget}
              onChange={e => setCustomBudget(e.target.value)}
              disabled={isLearning}
              className="input-glow"
              style={{
                width: '72px',
                padding: '8px 10px',
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                color: 'var(--text-primary)',
                fontSize: '13px',
                fontFamily: 'inherit',
                opacity: isLearning ? 0.4 : 1,
              }}
            />
            <button
              onClick={handleCustomStart}
              disabled={isLearning}
              style={{
                padding: '8px 14px',
                background: isLearning ? 'transparent' : 'rgba(88, 166, 255, 0.15)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                color: isLearning ? 'var(--text-muted)' : 'var(--accent-blue)',
                fontSize: '12px',
                fontWeight: '600',
                fontFamily: 'inherit',
                cursor: isLearning ? 'not-allowed' : 'pointer',
                opacity: isLearning ? 0.4 : 1,
                transition: 'all 0.2s ease',
              }}
            >
              Start
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
