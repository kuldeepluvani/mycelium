"""Agent router — selects relevant agents for a query."""
from __future__ import annotations
from dataclasses import dataclass
from mycelium.serve.intent import QueryIntent


@dataclass
class RoutedAgent:
    agent_id: str
    agent_name: str
    relevance: float  # 0-1
    owned_nodes_in_subgraph: int


class AgentRouter:
    def __init__(self, max_agents: int = 3):
        self._max = max_agents

    def select(self, intent: QueryIntent, agents: list) -> list[RoutedAgent]:
        """Select top N agents by relevance to query subgraph."""
        if not agents or not intent.subgraph_ids:
            return []

        scored = []
        for agent in agents:
            if agent.status not in ("active", "mature"):
                continue
            agent_nodes = set(agent.node_ids)
            overlap = agent_nodes & intent.subgraph_ids
            if not overlap:
                continue
            relevance = len(overlap) / len(intent.subgraph_ids) if intent.subgraph_ids else 0
            scored.append(RoutedAgent(
                agent_id=agent.id,
                agent_name=agent.name,
                relevance=relevance,
                owned_nodes_in_subgraph=len(overlap),
            ))

        scored.sort(key=lambda x: x.relevance, reverse=True)
        return scored[:self._max]
