"""Parallel agent reasoning via Claude CLI."""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from mycelium.shared.llm import ClaudeCLI
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.serve.router import RoutedAgent

REASON_PROMPT = """You are "{agent_name}", a specialist in {domain}.

Query: {query}

Your domain knowledge (entities and relationships):
{context}

Answer the query using ONLY the knowledge provided. Cite specific entities.
If you don't have enough information, say what's missing.

Return your analysis as plain text."""


@dataclass
class AgentResponse:
    agent_id: str
    agent_name: str
    response: str
    success: bool = True
    call_cost: int = 1


class ParallelReasoner:
    def __init__(self, llm: ClaudeCLI):
        self._llm = llm

    async def reason(
        self,
        query: str,
        routed_agents: list[RoutedAgent],
        agent_details: dict,  # agent_id -> Agent object
        graph: KnowledgeGraph,
    ) -> list[AgentResponse]:
        tasks = []
        for ra in routed_agents:
            agent = agent_details.get(ra.agent_id)
            if not agent:
                continue
            tasks.append(self._reason_single(query, agent, graph))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        responses = []
        for r in results:
            if isinstance(r, AgentResponse):
                responses.append(r)
            elif isinstance(r, Exception):
                responses.append(AgentResponse(agent_id="error", agent_name="error", response=str(r), success=False))
        return responses

    async def _reason_single(self, query: str, agent, graph: KnowledgeGraph) -> AgentResponse:
        from mycelium.serve.context_builder import build_agent_context
        context = build_agent_context(graph, agent.node_ids, max_entities=30, max_neighbors=8)

        prompt = REASON_PROMPT.format(
            agent_name=agent.name,
            domain=agent.domain,
            query=query,
            context=context or "(no context)",
        )

        resp = await self._llm.generate(prompt)
        return AgentResponse(
            agent_id=agent.id,
            agent_name=agent.name,
            response=resp.content if resp.success else "",
            success=resp.success,
        )
