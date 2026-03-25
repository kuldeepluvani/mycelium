import { useEffect, useRef, useCallback } from 'react'
import * as d3 from 'd3'
import { getEntityColor } from '../../utils/colors'
import type { GraphNode, GraphEdge } from '../../hooks/useGraph'

interface SimNode extends d3.SimulationNodeDatum {
  id: string
  name: string
  entity_class: string
  confidence: number
}

interface SimLink extends d3.SimulationLinkDatum<SimNode> {
  confidence: number
  type?: string
}

interface ForceGraphProps {
  nodes: GraphNode[]
  edges: GraphEdge[]
  selectedNodeId?: string | null
  onSelectNode: (id: string) => void
}

export function ForceGraph({ nodes, edges, selectedNodeId, onSelectNode }: ForceGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const simulationRef = useRef<d3.Simulation<SimNode, SimLink> | null>(null)

  const buildGraph = useCallback(() => {
    const container = containerRef.current
    const svgEl = svgRef.current
    if (!svgEl || !container) return

    const width = container.clientWidth
    const height = container.clientHeight

    // Clear previous render
    d3.select(svgEl).selectAll('*').remove()

    const svg = d3
      .select(svgEl)
      .attr('width', width)
      .attr('height', height)

    // Defs: glow filter
    const defs = svg.append('defs')
    const filter = defs.append('filter').attr('id', 'glow')
    filter.append('feGaussianBlur').attr('stdDeviation', '3').attr('result', 'blur')
    const merge = filter.append('feMerge')
    merge.append('feMergeNode').attr('in', 'blur')
    merge.append('feMergeNode').attr('in', 'SourceGraphic')

    // Zoom
    const g = svg.append('g')
    svg.call(
      d3
        .zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on('zoom', (event) => {
          g.attr('transform', event.transform)
        })
    )

    // Prepare data (shallow copy so D3 can mutate positions)
    const simNodes: SimNode[] = nodes.map((n) => ({
      id: n.id,
      name: n.name,
      entity_class: n.entity_class,
      confidence: n.confidence,
    }))

    const nodeIndex = new Map(simNodes.map((n) => [n.id, n]))

    const simLinks: SimLink[] = edges
      .map((e) => ({
        source: String(e.source),
        target: String(e.target),
        confidence: e.confidence ?? 0.5,
        type: e.type,
      }))
      .filter((e) => nodeIndex.has(e.source) && nodeIndex.has(e.target))

    // Simulation
    const simulation = d3
      .forceSimulation<SimNode>(simNodes)
      .force('charge', d3.forceManyBody<SimNode>().strength(-150))
      .force(
        'link',
        d3
          .forceLink<SimNode, SimLink>(simLinks)
          .id((d) => d.id)
          .distance(80)
      )
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide<SimNode>().radius(15))

    simulationRef.current = simulation

    // Edges
    const link = g
      .append('g')
      .attr('class', 'links')
      .selectAll('line')
      .data(simLinks)
      .join('line')
      .attr('stroke', 'rgba(88, 166, 255, 0.2)')
      .attr('stroke-width', (d) => 0.5 + d.confidence * 1.5)
      .attr('stroke-linecap', 'round')

    // Node groups
    const node = g
      .append('g')
      .attr('class', 'nodes')
      .selectAll<SVGGElement, SimNode>('g')
      .data(simNodes)
      .join('g')
      .attr('cursor', 'pointer')
      .call(
        d3
          .drag<SVGGElement, SimNode>()
          .on('start', (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart()
            d.fx = d.x
            d.fy = d.y
          })
          .on('drag', (event, d) => {
            d.fx = event.x
            d.fy = event.y
          })
          .on('end', (event, d) => {
            if (!event.active) simulation.alphaTarget(0)
            d.fx = null
            d.fy = null
          })
      )

    // Circles
    node
      .append('circle')
      .attr('r', (d) => 4 + d.confidence * 8)
      .attr('fill', (d) => `${getEntityColor(d.entity_class)}33`)
      .attr('stroke', (d) => getEntityColor(d.entity_class))
      .attr('stroke-width', 1.5)
      .attr('filter', 'url(#glow)')

    // Labels — always show for high confidence, hover for others
    node
      .append('text')
      .attr('dy', (d) => -(5 + d.confidence * 8) - 4)
      .attr('text-anchor', 'middle')
      .attr('font-size', '10px')
      .attr('fill', (d) => getEntityColor(d.entity_class))
      .attr('pointer-events', 'none')
      .attr('class', 'node-label')
      .style('opacity', (d) => (d.confidence > 0.8 ? 1 : 0))
      .style(
        'text-shadow',
        (d) => `0 0 6px ${getEntityColor(d.entity_class)}`
      )
      .text((d) => d.name)

    // Interactions
    node
      .on('mouseenter', function (_, d) {
        // Highlight this node
        d3.select(this)
          .select('circle')
          .attr('stroke-width', 2.5)
          .attr('transform', 'scale(1.3)')

        // Show label
        d3.select(this).select('text').style('opacity', 1)

        // Dim unconnected edges
        const connectedNodeIds = new Set<string>()
        connectedNodeIds.add(d.id)
        simLinks.forEach((l) => {
          const srcId = typeof l.source === 'object' ? (l.source as SimNode).id : String(l.source)
          const tgtId = typeof l.target === 'object' ? (l.target as SimNode).id : String(l.target)
          if (srcId === d.id || tgtId === d.id) {
            connectedNodeIds.add(srcId)
            connectedNodeIds.add(tgtId)
          }
        })

        link
          .attr('stroke', (l) => {
            const srcId = typeof l.source === 'object' ? (l.source as SimNode).id : l.source
            const tgtId = typeof l.target === 'object' ? (l.target as SimNode).id : l.target
            return srcId === d.id || tgtId === d.id
              ? 'rgba(88, 166, 255, 0.7)'
              : 'rgba(88, 166, 255, 0.05)'
          })

        node.style('opacity', (n) => (connectedNodeIds.has(n.id) ? 1 : 0.2))
      })
      .on('mouseleave', function (_, d) {
        d3.select(this)
          .select('circle')
          .attr('stroke-width', 1.5)
          .attr('transform', null)

        d3.select(this)
          .select('text')
          .style('opacity', d.confidence > 0.8 ? 1 : 0)

        link.attr('stroke', 'rgba(88, 166, 255, 0.2)')
        node.style('opacity', 1)
      })
      .on('click', (_, d) => {
        onSelectNode(d.id)
      })

    // Highlight selected node
    node.select('circle').attr('stroke-width', (d) =>
      d.id === selectedNodeId ? 3 : 1.5
    )

    // Tick
    simulation.on('tick', () => {
      link
        .attr('x1', (d) => (d.source as SimNode).x ?? 0)
        .attr('y1', (d) => (d.source as SimNode).y ?? 0)
        .attr('x2', (d) => (d.target as SimNode).x ?? 0)
        .attr('y2', (d) => (d.target as SimNode).y ?? 0)

      node.attr('transform', (d) => `translate(${d.x ?? 0},${d.y ?? 0})`)
    })

    // Subtle ambient animation: after simulation cools, keep a tiny alpha alive
    simulation.on('end', () => {
      simulation.alpha(0.005).restart()
    })
  }, [nodes, edges, selectedNodeId, onSelectNode])

  useEffect(() => {
    buildGraph()
    return () => {
      simulationRef.current?.stop()
    }
  }, [buildGraph])

  // Handle resize
  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const observer = new ResizeObserver(() => buildGraph())
    observer.observe(container)
    return () => observer.disconnect()
  }, [buildGraph])

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', position: 'relative' }}>
      <svg ref={svgRef} style={{ width: '100%', height: '100%', display: 'block' }} />
    </div>
  )
}
