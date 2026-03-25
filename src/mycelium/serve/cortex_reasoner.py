"""Hierarchical reasoning: L2 coordination -> L1 execution -> L2 synthesis."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from mycelium.shared.llm import ClaudeCLI
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.network.agent import Agent
from mycelium.network.meta_agent import MetaAgent
from mycelium.serve.cortex_router import CortexRoute

L1_REASON_PROMPT = """You are "{agent_name}", a specialist in {domain}.
Your supervisor "{coordinator}" has delegated this query to you.

Query: {query}

Your domain knowledge:
{context}

Answer using ONLY the knowledge provided. Cite specific entities.
If you lack information, say what's missing."""

L2_SYNTHESIS_PROMPT = """You are "{meta_name}", coordinating these specialists:
{children_info}

Query: {query}

Specialist responses:
{responses}

Synthesize a unified answer. Resolve contradictions. Note gaps.
Credit each specialist."""


@dataclass
class L1Response:
    agent_id: str
    agent_name: str
    response: str
    success: bool = True


@dataclass
class CortexResponse:
    coordinated_by: str
    l1_responses: list[L1Response] = field(default_factory=list)
    synthesis: str = ""
    delegation_mode: str = ""


class CortexReasoner:
    def __init__(self, llm: ClaudeCLI):
        self._llm = llm

    async def reason(
        self,
        query: str,
        route: CortexRoute,
        meta_agents: dict[str, MetaAgent],
        l1_agents: dict[str, Agent],
        graph: KnowledgeGraph,
    ) -> CortexResponse:
        coordinator_name = route.meta_agent_name or "System"
        meta = meta_agents.get(route.meta_agent_id or "")

        target_ids = route.strategy.target_ids or route.fallback_agent_ids
        tasks = []
        for agent_id in target_ids:
            agent = l1_agents.get(agent_id)
            if agent:
                tasks.append(
                    self._reason_l1(query, agent, coordinator_name, graph)
                )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        l1_responses = []
        for r in results:
            if isinstance(r, L1Response):
                l1_responses.append(r)
            elif isinstance(r, Exception):
                l1_responses.append(
                    L1Response(
                        agent_id="error",
                        agent_name="error",
                        response=str(r),
                        success=False,
                    )
                )

        synthesis = ""
        if (
            route.strategy.mode == "fanout"
            and len(l1_responses) >= 2
            and meta
        ):
            synthesis = await self._synthesize_l2(query, meta, l1_responses)

        return CortexResponse(
            coordinated_by=coordinator_name,
            l1_responses=l1_responses,
            synthesis=synthesis,
            delegation_mode=route.strategy.mode,
        )

    async def _reason_l1(
        self,
        query: str,
        agent: Agent,
        coordinator: str,
        graph: KnowledgeGraph,
    ) -> L1Response:
        context_lines = []
        for nid in agent.node_ids[:15]:
            e = graph.get_entity(nid)
            if e:
                neighbors = graph.get_neighbors(nid)
                neighbor_names = []
                for neighbor_id in list(neighbors)[:5]:
                    n = graph.get_entity(neighbor_id)
                    if n:
                        neighbor_names.append(n.name)
                context_lines.append(
                    f"- {e.name} ({e.entity_class}): "
                    f"connected to {', '.join(neighbor_names) or 'nothing'}"
                )

        prompt = L1_REASON_PROMPT.format(
            agent_name=agent.name,
            domain=agent.domain,
            coordinator=coordinator,
            query=query,
            context="\n".join(context_lines) or "(no context)",
        )
        resp = await self._llm.generate(prompt)
        return L1Response(
            agent_id=agent.id,
            agent_name=agent.name,
            response=resp.content if resp.success else "",
            success=resp.success,
        )

    async def _synthesize_l2(
        self,
        query: str,
        meta: MetaAgent,
        responses: list[L1Response],
    ) -> str:
        children_info = "\n".join(
            f"- {c.agent_name} ({c.domain}): "
            f"{c.entity_count} entities, confidence {c.confidence:.0%}"
            for c in meta.children
        )
        responses_text = "\n\n".join(
            f"**{r.agent_name}:** {r.response}"
            for r in responses
            if r.success
        )
        prompt = L2_SYNTHESIS_PROMPT.format(
            meta_name=meta.name,
            children_info=children_info,
            query=query,
            responses=responses_text,
        )
        resp = await self._llm.generate(prompt)
        return resp.content if resp.success else ""
