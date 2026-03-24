"""Tests for mycelium.serve.synthesizer."""
from __future__ import annotations
import asyncio
from unittest.mock import AsyncMock
from mycelium.shared.llm import CLIResponse
from mycelium.serve.reasoner import AgentResponse
from mycelium.serve.synthesizer import Synthesizer


def test_synthesize_combines_responses():
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=CLIResponse(
        content=(
            "ANSWER: Redis is a cache, Postgres is a DB.\n\n"
            "RATIONALE:\n"
            "- Redis is in-memory (from: Agent1)\n"
            "- Postgres is relational (from: Agent2)\n\n"
            "UNKNOWNS:\n"
            "- Connection pooling config\n\n"
            "FOLLOW-UPS:\n"
            "- What is the failover strategy?"
        ),
        duration_ms=200,
        success=True,
    ))

    synth = Synthesizer(llm)
    responses = [
        AgentResponse(agent_id="a1", agent_name="Agent1", response="Redis is in-memory cache."),
        AgentResponse(agent_id="a2", agent_name="Agent2", response="Postgres is relational DB."),
    ]

    result = asyncio.get_event_loop().run_until_complete(
        synth.synthesize("compare redis and postgres", responses)
    )
    assert result.success
    assert "Redis" in result.answer
    assert len(result.rationale_chain) >= 1
    assert len(result.unknowns) >= 1
    assert len(result.follow_ups) >= 1


def test_no_responses():
    llm = AsyncMock()
    synth = Synthesizer(llm)
    result = asyncio.get_event_loop().run_until_complete(synth.synthesize("query", []))
    assert not result.success
    assert "No agents" in result.answer


def test_llm_failure():
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value=CLIResponse(content="", duration_ms=100, success=False, error="fail"))

    synth = Synthesizer(llm)
    responses = [AgentResponse(agent_id="a1", agent_name="Agent1", response="OK")]

    result = asyncio.get_event_loop().run_until_complete(
        synth.synthesize("query", responses)
    )
    assert not result.success
