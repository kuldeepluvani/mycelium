import { useAsk } from '../../hooks/useAsk'
import { QueryInput } from './QueryInput'
import { RoutingFlow } from './RoutingFlow'
import { ResponsePanel } from './ResponsePanel'
import { QueryHistory } from './QueryHistory'

export function AskPage() {
  const {
    query,
    setQuery,
    mode,
    setMode,
    result,
    loading,
    history,
    routingSteps,
    error,
    submitQuery,
    loadHistoryItem,
  } = useAsk()

  function handleSubmit() {
    submitQuery(query, mode)
  }

  function handleFollowUp(q: string) {
    setQuery(q)
    submitQuery(q, mode)
  }

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>
      {/* Left sidebar — history */}
      <QueryHistory history={history} onSelect={loadHistoryItem} />

      {/* Main area */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          padding: '16px',
          gap: '16px',
        }}
      >
        {/* Input at top */}
        <QueryInput
          query={query}
          mode={mode}
          loading={loading}
          onQueryChange={setQuery}
          onModeChange={setMode}
          onSubmit={handleSubmit}
        />

        {/* Scrollable content below input */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Error */}
          {error && (
            <div
              className="glass-panel p-4 text-sm"
              style={{
                color: 'var(--accent-orange)',
                borderColor: 'rgba(255, 166, 87, 0.3)',
              }}
            >
              Error: {error}
            </div>
          )}

          {/* Routing flow visualization */}
          {(routingSteps.length > 0 || loading) && (
            <RoutingFlow
              query={query}
              steps={routingSteps}
              mode={result?.mode ?? mode}
            />
          )}

          {/* Response panel */}
          {result && !loading && (
            <ResponsePanel result={result} onFollowUp={handleFollowUp} />
          )}

          {/* Empty state */}
          {!result && !loading && !error && (
            <div
              className="flex items-center justify-center"
              style={{ flex: 1, minHeight: '200px' }}
            >
              <div className="text-center">
                <div
                  className="text-4xl mb-4"
                  style={{
                    color: 'rgba(88, 166, 255, 0.2)',
                    animation: 'pulse-glow 3s ease-in-out infinite',
                  }}
                >
                  ⬡
                </div>
                <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
                  Ask a question to activate the agent network
                </div>
                <div className="text-xs mt-1" style={{ color: 'rgba(230, 237, 243, 0.25)' }}>
                  ⌘+Enter to submit
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
