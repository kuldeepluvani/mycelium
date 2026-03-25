import { useState, useEffect, useCallback, useRef } from 'react'
import { api } from '../api/client'
import { wsManager } from '../api/websocket'

export interface LearnSession {
  id: string
  status: 'completed' | 'running' | 'interrupted'
  budget: number
  spent: number
  entities_created: number
  edges_created: number
  agents_discovered?: number
  agents_spawned?: number
  spillovers?: number
  documents_processed?: string[]
  started_at: string
  completed_at?: string
}

export interface LearnProgress {
  spent: number
  budget: number
}

export interface LiveEvent {
  id: string
  type: string
  timestamp: number
  [key: string]: any
}

export function useLearn() {
  const [sessions, setSessions] = useState<LearnSession[]>([])
  const [isLearning, setIsLearning] = useState(false)
  const [progress, setProgress] = useState<LearnProgress>({ spent: 0, budget: 0 })
  const [liveEvents, setLiveEvents] = useState<LiveEvent[]>([])
  const [selectedSession, setSelectedSession] = useState<LearnSession | null>(null)
  const [loading, setLoading] = useState(true)
  const eventIdRef = useRef(0)

  const fetchSessions = useCallback(async () => {
    try {
      const res = await api.learnSessions()
      setSessions(res?.sessions ?? res ?? [])
    } catch (err) {
      console.error('Failed to fetch learn sessions', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchSessions()
  }, [fetchSessions])

  useEffect(() => {
    const unsub = wsManager.subscribe((event: any) => {
      if (!event?.type?.startsWith('learn.')) return

      const id = String(++eventIdRef.current)
      const liveEvent: LiveEvent = { ...event, id, timestamp: Date.now() }

      setLiveEvents(prev => [...prev, liveEvent])

      if (event.type === 'learn.started') {
        setIsLearning(true)
        setLiveEvents([liveEvent])
      }

      if (event.type === 'learn.progress') {
        setProgress({ spent: event.spent ?? 0, budget: event.budget ?? 0 })
      }

      if (event.type === 'learn.complete') {
        setIsLearning(false)
        fetchSessions()
      }
    })

    return () => { unsub() }
  }, [fetchSessions])

  const startLearn = useCallback(async (budget: number) => {
    try {
      setLiveEvents([])
      setProgress({ spent: 0, budget })
      await api.learnStart(budget)
      setIsLearning(true)
    } catch (err) {
      console.error('Failed to start learn', err)
    }
  }, [])

  const cancelLearn = useCallback(async () => {
    try {
      await api.learnCancel()
      setIsLearning(false)
      fetchSessions()
    } catch (err) {
      console.error('Failed to cancel learn', err)
      setIsLearning(false)
    }
  }, [fetchSessions])

  return {
    sessions,
    isLearning,
    progress,
    liveEvents,
    selectedSession,
    setSelectedSession,
    loading,
    startLearn,
    cancelLearn,
  }
}
