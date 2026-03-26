"""Reusable query engine — used by CLI and API."""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class QueryResult:
    answer: str
    agents_used: list[str] = field(default_factory=list)
    coordinated_by: str | None = None
    mode: str = ""
    rationale: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    route_meta_id: str | None = None
    route_strategy: str | None = None
    l1_agent_ids: list[str] = field(default_factory=list)
    mentioned_entities: list[str] = field(default_factory=list)
    mentioned_entity_ids: list[str] = field(default_factory=list)
    mentioned_relationship_ids: list[str] = field(default_factory=list)


class QueryEngine:
    def __init__(self, orch):
        self._orch = orch

    async def ask(self, query: str, mode: str = "auto") -> QueryResult:
        from mycelium.serve.intent import IntentParser
        intent = IntentParser(self._orch.graph).parse(query)
        metas = self._orch.agent_manager.get_meta_agents()

        if metas and mode != "flat":
            return await self._ask_cortex(query, intent, metas)
        return await self._ask_flat(query, intent)

    async def _ask_cortex(self, query, intent, metas) -> QueryResult:
        from mycelium.serve.cortex_router import CortexRouter
        from mycelium.serve.cortex_reasoner import CortexReasoner

        active = self._orch.agent_manager.get_active()
        router = CortexRouter(max_l1_agents=3)
        route = router.route(intent, meta_agents=metas, l1_agents=active)

        reasoner = CortexReasoner(llm=self._orch._llm)
        resp = await reasoner.reason(
            query=query, route=route,
            meta_agents={m.id: m for m in metas},
            l1_agents={a.id: a for a in active},
            graph=self._orch.graph,
        )

        answer = resp.synthesis if resp.synthesis else (
            resp.l1_responses[0].response if resp.l1_responses else "No agents could answer."
        )

        entity_ids = []
        for name in intent.mentioned_entities:
            for eid in self._orch.graph.all_entity_ids():
                e = self._orch.graph.get_entity(eid)
                if e and e.name.lower() == name.lower():
                    entity_ids.append(eid)
                    break

        return QueryResult(
            answer=answer,
            agents_used=[r.agent_name for r in resp.l1_responses if r.success],
            coordinated_by=resp.coordinated_by,
            mode=resp.delegation_mode,
            route_meta_id=route.meta_agent_id,
            route_strategy=route.strategy.mode,
            l1_agent_ids=route.strategy.target_ids or route.fallback_agent_ids,
            mentioned_entities=intent.mentioned_entities,
            mentioned_entity_ids=entity_ids,
        )

    async def _ask_flat(self, query, intent) -> QueryResult:
        from mycelium.serve.router import AgentRouter, RoutedAgent
        from mycelium.serve.reasoner import ParallelReasoner
        from mycelium.serve.synthesizer import Synthesizer

        agents = AgentRouter().select(intent, self._orch.agent_manager.agents)
        if not agents:
            active = self._orch.agent_manager.get_active()
            if active:
                agents = [
                    RoutedAgent(agent_id=a.id, agent_name=a.name, relevance=0.5,
                                owned_nodes_in_subgraph=len(a.node_ids))
                    for a in active[:3]
                ]
            else:
                return QueryResult(answer="No agents available. Run 'mycelium learn' first.")

        agent_details = {a.agent_id: self._orch.agent_manager.get(a.agent_id) for a in agents}
        reasoner = ParallelReasoner(self._orch._llm)
        responses = await reasoner.reason(query, agents, agent_details, self._orch.graph)

        synthesizer = Synthesizer(self._orch._llm)
        result = await synthesizer.synthesize(query, responses)

        entity_ids = []
        for name in intent.mentioned_entities:
            for eid in self._orch.graph.all_entity_ids():
                e = self._orch.graph.get_entity(eid)
                if e and e.name.lower() == name.lower():
                    entity_ids.append(eid)
                    break

        return QueryResult(
            answer=result.answer,
            rationale=result.rationale_chain,
            unknowns=result.unknowns,
            follow_ups=result.follow_ups,
            agents_used=[a.agent_name for a in agents],
            mode="flat",
            l1_agent_ids=[a.agent_id for a in agents],
            mentioned_entities=intent.mentioned_entities,
            mentioned_entity_ids=entity_ids,
        )
