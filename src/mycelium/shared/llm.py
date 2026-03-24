"""Claude CLI async wrapper with retry and timeout."""
from __future__ import annotations
import asyncio
import json
import time
from dataclasses import dataclass


@dataclass
class CLIResponse:
    content: str
    duration_ms: int
    success: bool
    error: str | None = None


class ClaudeCLI:
    def __init__(self, timeout: int = 60, max_retries: int = 2):
        self._timeout = timeout
        self._max_retries = max_retries

    async def generate(self, prompt: str, system: str | None = None) -> CLIResponse:
        """Run claude -p with prompt, return response."""
        args = ["claude", "-p", prompt]
        if system:
            args.extend(["--system", system])

        for attempt in range(self._max_retries + 1):
            start = time.monotonic()
            try:
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=self._timeout
                )
                duration = int((time.monotonic() - start) * 1000)

                if proc.returncode == 0:
                    return CLIResponse(
                        content=stdout.decode().strip(),
                        duration_ms=duration,
                        success=True,
                    )
                else:
                    error = stderr.decode().strip()
                    if attempt < self._max_retries:
                        await asyncio.sleep(2 ** attempt)  # exponential backoff
                        continue
                    return CLIResponse(content="", duration_ms=duration, success=False, error=error)

            except asyncio.TimeoutError:
                duration = int((time.monotonic() - start) * 1000)
                if attempt < self._max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return CLIResponse(content="", duration_ms=duration, success=False, error="Timeout")

    async def generate_json(self, prompt: str, system: str | None = None) -> dict | None:
        """Run claude -p and parse JSON response."""
        resp = await self.generate(prompt, system)
        if not resp.success:
            return None
        try:
            # Try to find JSON in the response (sometimes wrapped in markdown)
            content = resp.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            return json.loads(content)
        except (json.JSONDecodeError, IndexError):
            return None

    async def health_check(self) -> bool:
        """Verify Claude CLI is accessible."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10)
            return proc.returncode == 0
        except Exception:
            return False
