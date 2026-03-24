"""Single-instance process guard using PID file."""

from __future__ import annotations

import atexit
import os
from pathlib import Path


class ProcessGuard:
    def __init__(self, pid_path: Path):
        self.pid_path = pid_path
        self._owned = False

    def acquire(self) -> None:
        if self.pid_path.exists():
            try:
                existing_pid = int(self.pid_path.read_text().strip())
                os.kill(existing_pid, 0)  # check if alive
                raise RuntimeError(
                    f"Mycelium already running (PID {existing_pid}). "
                    f"Remove {self.pid_path} if this is stale."
                )
            except (ProcessLookupError, ValueError):
                self.pid_path.unlink(missing_ok=True)

        self.pid_path.parent.mkdir(parents=True, exist_ok=True)
        self.pid_path.write_text(str(os.getpid()))
        self._owned = True
        atexit.register(self.release)

    def release(self) -> None:
        if self._owned and self.pid_path.exists():
            try:
                pid = int(self.pid_path.read_text().strip())
                if pid == os.getpid():
                    self.pid_path.unlink(missing_ok=True)
            except (ValueError, OSError):
                pass
            self._owned = False
