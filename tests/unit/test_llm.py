"""Tests for Claude CLI async wrapper."""
from __future__ import annotations
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mycelium.shared.llm import CLIResponse, ClaudeCLI


@pytest.fixture
def cli():
    return ClaudeCLI(timeout=10, max_retries=0)


def _make_proc(returncode=0, stdout=b"", stderr=b""):
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


@pytest.mark.asyncio
async def test_generate_success(cli):
    proc = _make_proc(returncode=0, stdout=b"Hello world")
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        resp = await cli.generate("test prompt")
    assert resp.success is True
    assert resp.content == "Hello world"
    assert resp.error is None
    assert resp.duration_ms >= 0


@pytest.mark.asyncio
async def test_generate_timeout(cli):
    proc = AsyncMock()
    proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        # Patch wait_for to raise TimeoutError
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            resp = await cli.generate("slow prompt")
    assert resp.success is False
    assert resp.error == "Timeout"


@pytest.mark.asyncio
async def test_generate_json_parses(cli):
    data = {"entities": [{"name": "foo"}]}
    proc = _make_proc(returncode=0, stdout=json.dumps(data).encode())
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        result = await cli.generate_json("give me json")
    assert result == data


@pytest.mark.asyncio
async def test_generate_json_markdown_wrapped(cli):
    data = {"key": "value"}
    wrapped = f"Here is the result:\n```json\n{json.dumps(data)}\n```\nDone."
    proc = _make_proc(returncode=0, stdout=wrapped.encode())
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        result = await cli.generate_json("give me json")
    assert result == data


@pytest.mark.asyncio
async def test_health_check(cli):
    proc = _make_proc(returncode=0, stdout=b"1.0.0")
    with patch("asyncio.create_subprocess_exec", return_value=proc):
        assert await cli.health_check() is True
