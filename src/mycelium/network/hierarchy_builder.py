"""Builds L2 meta-agents by grouping L1 agents with shared entity domains."""
from __future__ import annotations

from uuid import uuid4

from mycelium.shared.llm import ClaudeCLI
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.network.agent import Agent
from mycelium.network.meta_agent import MetaAgent, ChildManifest

META_NAME_PROMPT = """These AI specialist agents work in related domains:

{agents_info}

Generate a name and description for a supervisor agent that coordinates them.

Return JSON:
{{"name": "...", "domain": "...", "description": "..."}}

Output ONLY valid JSON."""


class HierarchyBuilder:
    def __init__(self, llm: ClaudeCLI, min_group_size: int = 2):
        self._llm = llm
        self._min_group_size = min_group_size

    async def build(
        self, agents: list[Agent], graph: KnowledgeGraph
    ) -> list[MetaAgent]:
        active = [a for a in agents if a.status in ("active", "mature")]
        if len(active) < self._min_group_size:
            return []

        groups = self._group_by_entity_overlap(active, graph)

        meta_agents = []
        for group in groups:
            if len(group) < self._min_group_size:
                continue
            meta = await self._create_meta_agent(group, graph)
            if meta:
                for agent in group:
                    agent.parent_id = meta.id
                meta_agents.append(meta)

        return meta_agents

    def _group_by_entity_overlap(
        self, agents: list[Agent], graph: KnowledgeGraph
    ) -> list[list[Agent]]:
        agent_entities: dict[str, set[str]] = {}
        for agent in agents:
            ents: set[str] = set()
            for nid in agent.node_ids:
                e = graph.get_entity(nid)
                if e and e.domain:
                    ents.add(e.domain)
                if e:
                    ents.add(e.entity_class)
            agent_entities[agent.id] = ents

        assigned: set[str] = set()
        groups: list[list[Agent]] = []

        for agent in agents:
            if agent.id in assigned:
                continue
            group = [agent]
            assigned.add(agent.id)

            for other in agents:
                if other.id in assigned:
                    continue
                a_ents = agent_entities.get(agent.id, set())
                b_ents = agent_entities.get(other.id, set())
                if not a_ents or not b_ents:
                    continue
                overlap = len(a_ents & b_ents) / len(a_ents | b_ents)
                if overlap > 0.15:  # Lower threshold to group more agents
                    group.append(other)
                    assigned.add(other.id)

            groups.append(group)

        return groups

    async def _create_meta_agent(
        self, group: list[Agent], graph: KnowledgeGraph
    ) -> MetaAgent | None:
        children = []
        for agent in group:
            key_ents = []
            for nid in agent.node_ids[:10]:
                e = graph.get_entity(nid)
                if e:
                    key_ents.append(e.name)
            children.append(
                ChildManifest(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    domain=agent.domain,
                    confidence=agent.avg_confidence,
                    entity_count=len(agent.node_ids),
                    key_entities=key_ents,
                )
            )

        agents_info = "\n".join(
            f"- {a.name} ({a.domain}): {a.description or 'no desc'}"
            for a in group
        )
        prompt = META_NAME_PROMPT.format(agents_info=agents_info)
        result = await self._llm.generate_json(prompt)

        meta_id = f"meta-{uuid4().hex[:8]}"

        if not result:
            return MetaAgent(
                id=meta_id,
                name=f"Meta-{group[0].domain}",
                domain=group[0].domain,
                children=children,
            )

        return MetaAgent(
            id=meta_id,
            name=result.get("name", f"Meta-{group[0].domain}"),
            domain=result.get("domain", group[0].domain),
            description=result.get("description", ""),
            children=children,
        )
