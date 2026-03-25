"""Cross-domain knowledge transfer between agents."""
from __future__ import annotations
from dataclasses import dataclass, field
from uuid import uuid4
from mycelium.shared.llm import ClaudeCLI
from mycelium.shared.models import Relationship
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.network.agent import Agent

SPILLOVER_PROMPT = """Two AI agents specialize in different knowledge domains.

Agent A "{agent_a_name}" knows about:
{agent_a_context}

Agent B "{agent_b_name}" knows about:
{agent_b_context}

Cross-domain edges already exist:
{existing_edges}

What connections are MISSING that a senior engineer would see?
What risks exist at the boundary between these domains?

Return JSON:
{{
  "missing_connections": [
    {{"source": "...", "target": "...", "rel_type": "...", "rationale": "...", "spillover_type": "..."}}
  ]
}}

spillover_type must be one of: dependency_chain, shared_concept, causal_bridge, risk_propagation, knowledge_gap

Output ONLY valid JSON."""


@dataclass
class SpilloverResult:
    new_relationships: list[Relationship] = field(default_factory=list)
    call_cost: int = 0
    skipped: bool = False
    skip_reason: str = ""


class SpilloverEngine:
    def __init__(self, llm: ClaudeCLI, edge_threshold: int = 5):
        self._llm = llm
        self._threshold = edge_threshold

    async def analyze_pair(
        self, agent_a: Agent, agent_b: Agent, graph: KnowledgeGraph
    ) -> SpilloverResult:
        # Count inter-cluster edges
        a_nodes = set(agent_a.node_ids)
        b_nodes = set(agent_b.node_ids)

        cross_edges = []
        for nid in a_nodes:
            neighbors = graph.get_neighbors(nid)
            for neighbor in neighbors:
                if neighbor in b_nodes:
                    cross_edges.append((nid, neighbor))

        if len(cross_edges) < self._threshold:
            return SpilloverResult(
                skipped=True,
                skip_reason=f"insufficient_edges ({len(cross_edges)} < {self._threshold})",
            )

        # Build context summaries
        a_context = self._summarize_agent(agent_a, graph, limit=10)
        b_context = self._summarize_agent(agent_b, graph, limit=10)
        edges_text = "\n".join(f"- {s} <-> {t}" for s, t in cross_edges[:10])

        prompt = SPILLOVER_PROMPT.format(
            agent_a_name=agent_a.name,
            agent_a_context=a_context,
            agent_b_name=agent_b.name,
            agent_b_context=b_context,
            existing_edges=edges_text or "(none)",
        )

        result = await self._llm.generate_json(prompt)
        if not result:
            return SpilloverResult(call_cost=1)

        relationships = []
        for conn in result.get("missing_connections", []):
            rel = Relationship(
                id=f"spillover-{uuid4().hex[:8]}",
                source_id=conn.get("source", ""),
                target_id=conn.get("target", ""),
                rel_type=conn.get("rel_type", "related_to"),
                rel_category="semantic",
                rationale=conn.get("rationale", ""),
                confidence=0.6,
            )
            relationships.append(rel)

        return SpilloverResult(new_relationships=relationships, call_cost=1)

    def _summarize_agent(
        self, agent: Agent, graph: KnowledgeGraph, limit: int = 10
    ) -> str:
        lines = []
        for nid in agent.node_ids[:limit]:
            e = graph.get_entity(nid)
            if e:
                lines.append(
                    f"- {e.name} ({e.entity_class}): {e.description or 'no desc'}"
                )
        return "\n".join(lines) or "(no entities)"

    async def analyze_all_pairs(
        self, agents: list[Agent], graph: KnowledgeGraph
    ) -> list[SpilloverResult]:
        results = []
        active = [a for a in agents if a.status in ("active", "mature")]
        for i, a in enumerate(active):
            for b in active[i + 1 :]:
                result = await self.analyze_pair(a, b, graph)
                results.append(result)
        return results

    async def analyze_meta_pairs(
        self,
        meta_agents: list,  # list[MetaAgent]
        l1_agents: list[Agent],
        graph: KnowledgeGraph,
    ) -> list[SpilloverResult]:
        """L2-to-L2 spillover: analyze between meta-agent pairs."""
        results = []
        active_metas = [m for m in meta_agents if m.status == "active"]

        for i, meta_a in enumerate(active_metas):
            for meta_b in active_metas[i + 1 :]:
                a_nodes: set[str] = set()
                for agent in l1_agents:
                    if agent.parent_id == meta_a.id:
                        a_nodes.update(agent.node_ids)
                b_nodes: set[str] = set()
                for agent in l1_agents:
                    if agent.parent_id == meta_b.id:
                        b_nodes.update(agent.node_ids)

                synth_a = Agent(
                    id=meta_a.id,
                    name=meta_a.name,
                    domain=meta_a.domain,
                    node_ids=list(a_nodes),
                    status="active",
                )
                synth_b = Agent(
                    id=meta_b.id,
                    name=meta_b.name,
                    domain=meta_b.domain,
                    node_ids=list(b_nodes),
                    status="active",
                )

                result = await self.analyze_pair(synth_a, synth_b, graph)
                results.append(result)

        return results
