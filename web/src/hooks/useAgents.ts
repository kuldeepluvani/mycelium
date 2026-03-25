import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

export type AgentStatus = 'active' | 'mature' | 'retired'

export interface Agent {
  id: string
  name: string
  domain?: string
  status: AgentStatus
  entity_count?: number
  confidence?: number
  key_entities?: string[]
  knowledge_gaps?: string[]
  pinned?: boolean
  parent_id?: string | null
}

export interface MetaAgent {
  id: string
  name: string
  domain?: string
  description?: string
  children: Agent[]
}

export interface SpilloverRelationship {
  from_id: string
  to_id: string
  count?: number
  details?: string
}

export interface SpilloverData {
  relationships: SpilloverRelationship[]
}

export type ViewMode = 'tree' | 'spillover'

export function useAgents() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [metaAgents, setMetaAgents] = useState<MetaAgent[]>([])
  const [spillover, setSpillover] = useState<SpilloverData>({ relationships: [] })
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState<ViewMode>('tree')

  const fetchAll = useCallback(async () => {
    setLoading(true)
    try {
      const [agentsRes, hierarchyRes, spilloverRes] = await Promise.allSettled([
        api.agents(),
        api.hierarchy(),
        api.spillover(),
      ])

      if (agentsRes.status === 'fulfilled') {
        setAgents(agentsRes.value?.agents ?? [])
      }
      if (hierarchyRes.status === 'fulfilled') {
        setMetaAgents(hierarchyRes.value?.meta_agents ?? [])
      }
      if (spilloverRes.status === 'fulfilled') {
        const raw = spilloverRes.value
        setSpillover({
          relationships: raw?.relationships ?? raw?.spillover ?? [],
        })
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  const pinAgent = useCallback(async (id: string, pinned: boolean) => {
    await api.pinAgent(id, pinned)
    await fetchAll()
  }, [fetchAll])

  const renameAgent = useCallback(async (id: string, name: string) => {
    await api.renameAgent(id, name)
    await fetchAll()
  }, [fetchAll])

  const retireAgent = useCallback(async (id: string) => {
    await api.retireAgent(id)
    await fetchAll()
  }, [fetchAll])

  return {
    agents,
    metaAgents,
    spillover,
    loading,
    viewMode,
    setViewMode,
    pinAgent,
    renameAgent,
    retireAgent,
  }
}
