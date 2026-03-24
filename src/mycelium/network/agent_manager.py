"""Agent lifecycle management."""
from __future__ import annotations
from uuid import uuid4
from mycelium.shared.llm import ClaudeCLI
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.network.agent import Agent
from mycelium.network.cluster import ClusterInfo

AGENT_NAME_PROMPT = """These entities form a knowledge cluster:
{entities}

Generate a name and description for an AI agent that specializes in this domain.

Return JSON:
{{"name": "...", "domain": "...", "description": "..."}}

Output ONLY valid JSON."""


class AgentManager:
    def __init__(self, llm: ClaudeCLI, stability_cycles: int = 2):
        self._llm = llm
        self._stability_cycles = stability_cycles
        self._agents: dict[str, Agent] = {}

    @property
    def agents(self) -> list[Agent]:
        return list(self._agents.values())

    def get(self, agent_id: str) -> Agent | None:
        return self._agents.get(agent_id)

    def get_active(self) -> list[Agent]:
        return [a for a in self._agents.values() if a.status in ("active", "mature")]

    async def process_clusters(
        self, clusters: list[ClusterInfo], graph: KnowledgeGraph
    ) -> list[Agent]:
        """Process detected clusters -- create, update, or retire agents."""
        new_agents = []

        for cluster in clusters:
            cluster_nodes = set(cluster.node_ids)

            # Find existing agent with >50% node overlap
            existing = None
            for agent in self._agents.values():
                if agent.status == "retired":
                    continue
                agent_nodes = set(agent.node_ids)
                if not agent_nodes:
                    continue
                intersection = cluster_nodes & agent_nodes
                union = cluster_nodes | agent_nodes
                jaccard = len(intersection) / len(union) if union else 0
                if jaccard > 0.3:  # 30% overlap = same cluster
                    existing = agent
                    break

            if existing:
                existing.node_ids = cluster.node_ids
                if existing.status == "candidate":
                    existing.status = "active"
            else:
                agent = await self._create_agent(cluster, graph)
                if agent:
                    agent.status = "active"  # Activate immediately
                    self._agents[agent.id] = agent
                    new_agents.append(agent)

        # Retire agents whose clusters dissolved (unless pinned)
        for agent in list(self._agents.values()):
            if agent.status == "retired" or agent.pinned:
                continue
            cluster_id = (
                f"cluster-{agent.id.split('-')[-1]}" if "-" in agent.id else None
            )
            # Simple: if agent has no matching active cluster, retire
            if not any(c.cluster_id == cluster_id for c in clusters):
                # Check if >50% of agent's nodes still exist in some cluster
                agent_nodes = set(agent.node_ids)
                found_in_clusters = False
                for c in clusters:
                    overlap = len(agent_nodes & set(c.node_ids)) / max(
                        len(agent_nodes), 1
                    )
                    if overlap > 0.5:
                        found_in_clusters = True
                        break
                if not found_in_clusters and agent.status != "candidate":
                    agent.status = "retired"

        return new_agents

    async def _create_agent(
        self, cluster: ClusterInfo, graph: KnowledgeGraph
    ) -> Agent | None:
        entities_info = []
        for nid in cluster.node_ids[:20]:  # limit context
            e = graph.get_entity(nid)
            if e:
                entities_info.append(f"- {e.name} ({e.entity_class})")

        if not entities_info:
            return None

        prompt = AGENT_NAME_PROMPT.format(entities="\n".join(entities_info))
        result = await self._llm.generate_json(prompt)

        if not result:
            return Agent(
                id=f"agent-{uuid4().hex[:8]}",
                name=f"Agent {cluster.cluster_id}",
                domain="unknown",
                seed_nodes=cluster.node_ids[:10],
                node_ids=cluster.node_ids,
            )

        return Agent(
            id=f"agent-{uuid4().hex[:8]}",
            name=result.get("name", f"Agent {cluster.cluster_id}"),
            domain=result.get("domain", "unknown"),
            description=result.get("description", ""),
            seed_nodes=cluster.node_ids[:10],
            node_ids=cluster.node_ids,
        )

    def _find_agent_for_cluster(self, cluster_id: str) -> Agent | None:
        """Match cluster to existing agent by node overlap (>50% Jaccard)."""
        # Get cluster nodes from the cluster_id — we need to look up from recent detect() call
        # Since we don't store cluster_id on agents, match by node overlap
        best_agent = None
        best_overlap = 0.0
        for agent in self._agents.values():
            if agent.status == "retired":
                continue
            if not agent.node_ids:
                continue
            # We'll match in process_clusters where we have cluster.node_ids
            # This method is called with cluster_id but we need nodes — refactored below
        return best_agent

    # User overrides
    def merge(self, agent_id_a: str, agent_id_b: str) -> Agent | None:
        a = self._agents.get(agent_id_a)
        b = self._agents.get(agent_id_b)
        if not a or not b:
            return None
        a.node_ids = list(set(a.node_ids + b.node_ids))
        b.status = "retired"
        return a

    def rename(self, agent_id: str, new_name: str) -> bool:
        agent = self._agents.get(agent_id)
        if agent:
            agent.name = new_name
            return True
        return False

    def pin(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if agent:
            agent.pinned = True
            return True
        return False

    def retire(self, agent_id: str) -> bool:
        agent = self._agents.get(agent_id)
        if agent and not agent.pinned:
            agent.status = "retired"
            return True
        return False
