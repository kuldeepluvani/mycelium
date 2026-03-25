import { useState, useEffect, useMemo } from 'react'
import { api } from '../api/client'

export interface GraphNode {
  id: string
  name: string
  entity_class: string
  domain?: string
  confidence: number
  first_seen?: string
  last_seen?: string
  [key: string]: unknown
}

export interface GraphEdge {
  id?: string
  source: string
  target: string
  type?: string
  category?: string
  confidence: number
  rationale?: string
  [key: string]: unknown
}

export interface EntityDetail extends GraphNode {
  provenance?: string[]
  relationships?: Array<{
    type: string
    target_id: string
    target_name: string
    category?: string
    confidence: number
    rationale?: string
  }>
}

export function useGraph() {
  const [nodes, setNodes] = useState<GraphNode[]>([])
  const [edges, setEdges] = useState<GraphEdge[]>([])
  const [selectedNode, setSelectedNode] = useState<EntityDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filter state
  const [searchTerm, setSearchTerm] = useState('')
  const [entityClassFilter, setEntityClassFilter] = useState<Set<string>>(new Set())
  const [confidenceRange, setConfidenceRange] = useState<[number, number]>([0, 1])

  useEffect(() => {
    async function loadGraph() {
      try {
        setLoading(true)
        const [nodesRes, edgesRes] = await Promise.all([
          api.graphNodes(),
          api.graphEdges(),
        ])
        const loadedNodes = (nodesRes.nodes || []) as GraphNode[]
        setNodes(loadedNodes)
        // Map source_id/target_id → source/target for D3
        const mappedEdges = (edgesRes.edges || []).map((e: any) => ({
          ...e,
          source: e.source_id || e.source,
          target: e.target_id || e.target,
          type: e.rel_type || e.type,
          category: e.rel_category || e.category,
          confidence: e.confidence ?? 0.5,
        })) as GraphEdge[]
        setEdges(mappedEdges)
        // Default: all entity classes enabled
        const classes = new Set(loadedNodes.map((n) => n.entity_class).filter(Boolean))
        setEntityClassFilter(classes)
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load graph')
      } finally {
        setLoading(false)
      }
    }
    loadGraph()
  }, [])

  const filteredNodes = useMemo(() => {
    return nodes.filter((n) => {
      const matchesSearch =
        !searchTerm || n.name.toLowerCase().includes(searchTerm.toLowerCase())
      const matchesClass =
        entityClassFilter.size === 0 || entityClassFilter.has(n.entity_class)
      const matchesConfidence =
        n.confidence >= confidenceRange[0] && n.confidence <= confidenceRange[1]
      return matchesSearch && matchesClass && matchesConfidence
    })
  }, [nodes, searchTerm, entityClassFilter, confidenceRange])

  const filteredNodeIds = useMemo(
    () => new Set(filteredNodes.map((n) => n.id)),
    [filteredNodes]
  )

  const filteredEdges = useMemo(() => {
    return edges.filter(
      (e) =>
        filteredNodeIds.has(String(e.source)) && filteredNodeIds.has(String(e.target))
    )
  }, [edges, filteredNodeIds])

  async function selectNode(id: string) {
    if (!id) {
      setSelectedNode(null)
      return
    }
    try {
      const detail = await api.graphEntity(id)
      setSelectedNode(detail as EntityDetail)
    } catch {
      // Fall back to basic node info
      const basic = nodes.find((n) => n.id === id)
      if (basic) setSelectedNode(basic as EntityDetail)
    }
  }

  function deselectNode() {
    setSelectedNode(null)
  }

  function toggleEntityClass(cls: string) {
    setEntityClassFilter((prev) => {
      const next = new Set(prev)
      if (next.has(cls)) next.delete(cls)
      else next.add(cls)
      return next
    })
  }

  // Agent ownership map: nodeId → agentName
  const [agentMap, setAgentMap] = useState<Map<string, string>>(new Map())

  useEffect(() => {
    api.agents().then(res => {
      const map = new Map<string, string>()
      for (const agent of res.agents || []) {
        for (const nid of agent.node_ids || []) {
          map.set(nid, agent.name)
        }
      }
      setAgentMap(map)
    }).catch(() => {})
  }, [])

  return {
    nodes,
    edges,
    filteredNodes,
    filteredEdges,
    selectedNode,
    loading,
    error,
    searchTerm,
    setSearchTerm,
    entityClassFilter,
    toggleEntityClass,
    setEntityClassFilter,
    confidenceRange,
    setConfidenceRange,
    selectNode,
    deselectNode,
    agentMap,
  }
}
