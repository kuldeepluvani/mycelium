import { useEvents } from '../../hooks/useEvents'
import { EventStream } from './EventStream'
import { EventDetail } from './EventDetail'
import { HealthCards } from './HealthCards'

export function ObservePage() {
  const {
    filteredEvents,
    selectedEvent,
    setSelectedEvent,
    healthMetrics,
    filters,
    toggleFilter,
    loading,
  } = useEvents()

  return (
    <div className="flex flex-col h-full" style={{ overflow: 'hidden' }}>
      {/* Health cards row */}
      <div
        className="flex-shrink-0 px-4 py-3"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        {loading ? (
          <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Loading health data...
          </div>
        ) : (
          <HealthCards metrics={healthMetrics} />
        )}
      </div>

      {/* Main area: event stream + optional detail panel */}
      <div className="flex flex-1 min-h-0">
        {/* Event stream */}
        <div className="flex-1 min-w-0">
          {loading ? (
            <div className="flex items-center justify-center h-full">
              <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                Loading events...
              </span>
            </div>
          ) : (
            <EventStream
              events={filteredEvents}
              filters={filters}
              onToggleFilter={toggleFilter}
              selectedEvent={selectedEvent}
              onSelectEvent={setSelectedEvent}
            />
          )}
        </div>

        {/* Detail panel */}
        {selectedEvent && (
          <EventDetail
            event={selectedEvent}
            onClose={() => setSelectedEvent(null)}
          />
        )}
      </div>
    </div>
  )
}
