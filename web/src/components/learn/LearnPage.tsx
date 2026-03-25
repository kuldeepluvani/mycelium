import { useLearn } from '../../hooks/useLearn'
import { LearnControls } from './LearnControls'
import { LearnProgress } from './LearnProgress'
import { SessionHistory } from './SessionHistory'
import { GrowthChart } from './GrowthChart'

export function LearnPage() {
  const {
    sessions,
    isLearning,
    progress,
    liveEvents,
    selectedSession,
    setSelectedSession,
    loading,
    startLearn,
  } = useLearn()

  return (
    <div
      style={{
        height: '100%',
        overflow: 'auto',
        padding: '20px 24px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        boxSizing: 'border-box',
      }}
    >
      {/* Top row: controls + chart */}
      <div style={{ display: 'flex', gap: '16px', alignItems: 'flex-start' }}>
        <div style={{ flex: 1 }}>
          <LearnControls isLearning={isLearning} onStart={startLearn} />
        </div>
        <div style={{ flexShrink: 0 }}>
          <GrowthChart sessions={sessions} />
        </div>
      </div>

      {/* Progress (conditionally rendered) */}
      <LearnProgress
        isLearning={isLearning}
        progress={progress}
        liveEvents={liveEvents}
      />

      {/* Session history */}
      <SessionHistory
        sessions={sessions}
        selectedSession={selectedSession}
        onSelectSession={setSelectedSession}
        loading={loading}
      />
    </div>
  )
}
