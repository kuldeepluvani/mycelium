"""Synthesize agent responses into unified answer with rationale chain."""
from __future__ import annotations
from dataclasses import dataclass, field
from mycelium.shared.llm import ClaudeCLI
from mycelium.serve.reasoner import AgentResponse

SYNTHESIS_PROMPT = """Multiple specialist agents have analyzed this query:

Query: {query}

Agent responses:
{responses}

Synthesize a unified answer that:
1. Combines insights from all agents
2. Identifies where agents agree and disagree
3. Highlights unknowns or gaps
4. Suggests follow-up questions

Format your response as:

ANSWER: [unified answer]

RATIONALE:
- [claim 1] (from: [agent name])
- [claim 2] (from: [agent name])

UNKNOWNS:
- [what's missing]

FOLLOW-UPS:
- [suggested question]"""


@dataclass
class SynthesisResult:
    answer: str
    rationale_chain: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    follow_ups: list[str] = field(default_factory=list)
    call_cost: int = 1
    success: bool = True


class Synthesizer:
    def __init__(self, llm: ClaudeCLI):
        self._llm = llm

    async def synthesize(self, query: str, agent_responses: list[AgentResponse]) -> SynthesisResult:
        if not agent_responses:
            return SynthesisResult(answer="No agents available to answer.", call_cost=0, success=False)

        responses_text = "\n\n".join(
            f"**{ar.agent_name}:**\n{ar.response}" for ar in agent_responses if ar.success
        )

        if not responses_text:
            return SynthesisResult(answer="All agents failed to respond.", call_cost=0, success=False)

        prompt = SYNTHESIS_PROMPT.format(query=query, responses=responses_text)
        resp = await self._llm.generate(prompt)

        if not resp.success:
            return SynthesisResult(answer="Synthesis failed.", call_cost=1, success=False)

        # Parse sections from response
        content = resp.content
        answer = content  # Default: full response
        rationale = []
        unknowns = []
        follow_ups = []

        if "ANSWER:" in content:
            parts = content.split("RATIONALE:")
            answer = parts[0].replace("ANSWER:", "").strip()
            if len(parts) > 1:
                rest = parts[1]
                if "UNKNOWNS:" in rest:
                    rat_part, rest = rest.split("UNKNOWNS:", 1)
                    rationale = [l.strip().lstrip("- ") for l in rat_part.strip().split("\n") if l.strip().startswith("-")]
                    if "FOLLOW-UPS:" in rest:
                        unk_part, fu_part = rest.split("FOLLOW-UPS:", 1)
                        unknowns = [l.strip().lstrip("- ") for l in unk_part.strip().split("\n") if l.strip().startswith("-")]
                        follow_ups = [l.strip().lstrip("- ") for l in fu_part.strip().split("\n") if l.strip().startswith("-")]

        return SynthesisResult(
            answer=answer,
            rationale_chain=rationale,
            unknowns=unknowns,
            follow_ups=follow_ups,
        )
