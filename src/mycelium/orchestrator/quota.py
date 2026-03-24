"""Call budget tracker with spend ledger."""
from __future__ import annotations
from datetime import datetime, timezone
from dataclasses import dataclass, field


@dataclass
class CallRecord:
    call_number: int
    timestamp: datetime
    task_type: str
    module: str
    duration_ms: int = 0
    success: bool = True
    input_tokens_est: int = 0
    output_tokens_est: int = 0


class QuotaTracker:
    def __init__(self, budget: int):
        self._budget = budget
        self._spent = 0
        self._calls: list[CallRecord] = []

    @property
    def budget(self) -> int:
        return self._budget

    @property
    def spent(self) -> int:
        return self._spent

    @property
    def remaining(self) -> int:
        return max(0, self._budget - self._spent)

    @property
    def exhausted(self) -> bool:
        return self._spent >= self._budget

    @property
    def calls(self) -> list[CallRecord]:
        return list(self._calls)

    def can_spend(self, n: int = 1) -> bool:
        return self._spent + n <= self._budget

    def spend(self, task_type: str, module: str, duration_ms: int = 0, success: bool = True) -> CallRecord:
        self._spent += 1
        record = CallRecord(
            call_number=self._spent,
            timestamp=datetime.now(timezone.utc),
            task_type=task_type,
            module=module,
            duration_ms=duration_ms,
            success=success,
        )
        self._calls.append(record)
        return record

    def summary(self) -> dict:
        return {
            "budget": self._budget,
            "spent": self._spent,
            "remaining": self.remaining,
            "exhausted": self.exhausted,
            "calls": len(self._calls),
        }
