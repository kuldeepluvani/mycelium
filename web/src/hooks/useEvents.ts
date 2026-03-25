import { useState, useEffect, useCallback, useMemo } from 'react'
import { api } from '../api/client'
import { wsManager } from '../api/websocket'

export type EventCategory = 'perception' | 'network' | 'serve' | 'orchestrator' | 'system'

export interface MyceliumEvent {
  id?: string
  event_type: string
  subject?: string
  module?: string
  payload?: Record<string, unknown>
  timestamp?: string
  [key: string]: unknown
}

export interface HealthMetric {
  module: string
  status: 'healthy' | 'degraded' | 'error'
  metric_name?: string
  metric_value?: number | string
  last_check?: string
  [key: string]: unknown
}

export const CATEGORY_COLORS: Record<EventCategory, string> = {
  perception: '#58a6ff',
  network: '#7ee787',
  serve: '#d2a8ff',
  orchestrator: '#ffa657',
  system: '#f85149',
}

export function getEventCategory(event_type: string): EventCategory {
  const t = event_type?.toLowerCase() ?? ''
  if (t.startsWith('perception.')) return 'perception'
  if (t.startsWith('network.')) return 'network'
  if (t.startsWith('serve.') || t.startsWith('ask.')) return 'serve'
  if (t.startsWith('orchestrator.') || t.startsWith('learn.')) return 'orchestrator'
  return 'system'
}

export function useEvents() {
  const [events, setEvents] = useState<MyceliumEvent[]>([])
  const [selectedEvent, setSelectedEvent] = useState<MyceliumEvent | null>(null)
  const [healthMetrics, setHealthMetrics] = useState<HealthMetric[]>([])
  const [filters, setFilters] = useState<Set<EventCategory>>(
    new Set<EventCategory>(['perception', 'network', 'serve', 'orchestrator', 'system'])
  )
  const [loading, setLoading] = useState(true)

  const fetchInitial = useCallback(async () => {
    setLoading(true)
    try {
      const [eventsRes, healthRes] = await Promise.allSettled([
        api.observeEvents(100),
        api.observeHealth(),
      ])

      if (eventsRes.status === 'fulfilled') {
        const raw = eventsRes.value
        const rawList = Array.isArray(raw) ? raw : raw?.events ?? []
        // Parse payload JSON strings
        const list: MyceliumEvent[] = rawList.map((e: any) => ({
          ...e,
          payload: typeof e.payload === 'string' ? (() => { try { return JSON.parse(e.payload) } catch { return { raw: e.payload } } })() : e.payload,
        }))
        // Newest first
        setEvents([...list].reverse())
      }

      if (healthRes.status === 'fulfilled') {
        const raw = healthRes.value
        const list: HealthMetric[] = Array.isArray(raw)
          ? raw
          : raw?.metrics ?? raw?.health ?? raw?.modules ?? []
        setHealthMetrics(list)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchInitial()
  }, [fetchInitial])

  // WebSocket subscription — push new events to front
  useEffect(() => {
    const unsub = wsManager.subscribe((event: MyceliumEvent) => {
      setEvents(prev => [event, ...prev])
    })
    return () => { unsub() }
  }, [])

  const toggleFilter = useCallback((category: EventCategory) => {
    setFilters(prev => {
      const next = new Set(prev)
      if (next.has(category)) {
        next.delete(category)
      } else {
        next.add(category)
      }
      return next
    })
  }, [])

  const filteredEvents = useMemo(() => {
    return events.filter(e => filters.has(getEventCategory(e.event_type)))
  }, [events, filters])

  return {
    events,
    filteredEvents,
    selectedEvent,
    setSelectedEvent,
    healthMetrics,
    filters,
    toggleFilter,
    loading,
  }
}
