import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

export type AskMode = 'auto' | 'cortex' | 'flat'

export interface AskResult {
  answer: string
  agents_used: string[]
  coordinated_by?: string
  mode: string
  route_meta_id?: string
  route_strategy?: string
  l1_agent_ids?: string[]
  mentioned_entities?: string[]
  rationale?: string
  unknowns?: string[]
  follow_ups?: string[]
}

export interface HistoryItem {
  query: string
  mode: AskMode
  result: AskResult
  timestamp: string
}

export type RoutingStepType = 'intent' | 'l2_routed' | 'l1_activated' | 'synthesis'

export interface RoutingStep {
  type: RoutingStepType
  entities?: string[]
  meta?: string
  strategy?: string
  agents?: string[]
  answer?: string
}

export function useAsk() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<AskMode>('auto')
  const [result, setResult] = useState<AskResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [routingSteps, setRoutingSteps] = useState<RoutingStep[]>([])
  const [error, setError] = useState<string | null>(null)

  const fetchHistory = useCallback(async () => {
    try {
      const res = await api.askHistory()
      setHistory(res?.queries ?? [])
    } catch {
      // history is best-effort
    }
  }, [])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  const buildRoutingSteps = useCallback((res: AskResult): RoutingStep[] => {
    const steps: RoutingStep[] = []

    steps.push({
      type: 'intent',
      entities: res.mentioned_entities ?? [],
    })

    if (res.mode === 'cortex' && res.coordinated_by) {
      steps.push({
        type: 'l2_routed',
        meta: res.coordinated_by,
        strategy: res.route_strategy ?? 'direct',
      })
    }

    steps.push({
      type: 'l1_activated',
      agents: res.agents_used ?? [],
    })

    steps.push({
      type: 'synthesis',
      answer: res.answer,
    })

    return steps
  }, [])

  const submitQuery = useCallback(async (q: string, m: AskMode = mode) => {
    if (!q.trim()) return
    setLoading(true)
    setError(null)
    setResult(null)
    setRoutingSteps([])
    try {
      const res = await api.ask(q.trim(), m)
      setResult(res)
      setRoutingSteps(buildRoutingSteps(res))
      // prepend to history locally
      setHistory(prev => [
        { query: q.trim(), mode: m, result: res, timestamp: new Date().toISOString() },
        ...prev,
      ])
    } catch (err: any) {
      setError(err?.message ?? 'Request failed')
    } finally {
      setLoading(false)
    }
  }, [mode, buildRoutingSteps])

  const loadHistoryItem = useCallback((item: HistoryItem) => {
    setQuery(item.query)
    setMode(item.mode)
    setResult(item.result)
    setRoutingSteps(buildRoutingSteps(item.result))
  }, [buildRoutingSteps])

  return {
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
  }
}
