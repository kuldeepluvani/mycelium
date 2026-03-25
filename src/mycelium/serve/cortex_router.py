"""Two-tier cortex router: L2 meta-agents -> L1 specialists."""
from __future__ import annotations

from dataclasses import dataclass, field

from mycelium.serve.intent import QueryIntent
from mycelium.network.agent import Agent
from mycelium.network.meta_agent import MetaAgent, DelegationStrategy


@dataclass
class CortexRoute:
    meta_agent_id: str | None = None
    meta_agent_name: str | None = None
    strategy: DelegationStrategy = field(
        default_factory=lambda: DelegationStrategy(mode="self")
    )
    fallback_agent_ids: list[str] = field(default_factory=list)


class CortexRouter:
    def __init__(self, max_l1_agents: int = 3):
        self._max_l1 = max_l1_agents

    def route(
        self,
        intent: QueryIntent,
        meta_agents: list[MetaAgent],
        l1_agents: list[Agent],
    ) -> CortexRoute:
        query_entities = set(intent.mentioned_entities)

        # Collect entity names for matching against child key_entities
        entity_names: set[str] = set()
        for eid in query_entities:
            entity_names.add(eid)  # IDs double as lookup keys

        best_meta: MetaAgent | None = None
        best_coverage = 0.0

        for meta in meta_agents:
            if meta.status != "active":
                continue

            # Score by subgraph node overlap with children's node_ids
            child_nodes: set[str] = set()
            for child in meta.children:
                l1 = next(
                    (a for a in l1_agents if a.id == child.agent_id), None
                )
                if l1:
                    child_nodes.update(l1.node_ids)

            if intent.subgraph_ids and child_nodes:
                coverage = len(child_nodes & intent.subgraph_ids) / len(
                    intent.subgraph_ids
                )
                if coverage > best_coverage:
                    best_coverage = coverage
                    best_meta = meta

        if best_meta and best_coverage > 0:
            # Build entity set from mentioned entity names for delegation
            child_entity_names: set[str] = set()
            for child in best_meta.children:
                child_entity_names.update(child.key_entities)

            strategy = best_meta.pick_strategy(entity_names or child_entity_names)
            if len(strategy.target_ids) > self._max_l1:
                strategy.target_ids = strategy.target_ids[: self._max_l1]
            return CortexRoute(
                meta_agent_id=best_meta.id,
                meta_agent_name=best_meta.name,
                strategy=strategy,
            )

        # Fallback: flat routing for orphan L1s
        orphans = [
            a
            for a in l1_agents
            if a.parent_id is None and a.status in ("active", "mature")
        ]
        fallback_ids = []
        for agent in orphans:
            if intent.subgraph_ids and (
                set(agent.node_ids) & intent.subgraph_ids
            ):
                fallback_ids.append(agent.id)

        return CortexRoute(fallback_agent_ids=fallback_ids[: self._max_l1])
