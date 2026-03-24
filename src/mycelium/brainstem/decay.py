"""Confidence decay engine — manages entity/relationship lifecycle."""
from __future__ import annotations
from mycelium.shared.config import DecayConfig


class DecayEngine:
    def __init__(self, config: DecayConfig):
        self._config = config
        self._rates = {
            "structural": config.structural,
            "causal": config.causal,
            "semantic": config.semantic,
            "temporal": config.temporal,
        }

    def apply_decay(self, confidence: float, rel_category: str) -> float:
        rate = self._rates.get(rel_category, 0.05)  # default 0.05 for unknown categories
        return confidence * (1.0 - rate)

    def boost(self, confidence: float, amount: float = 0.05) -> float:
        return min(0.99, confidence + amount)

    def feedback_boost(self, confidence: float) -> float:
        """Bounded feedback: +0.03, cap 0.99"""
        return min(0.99, confidence + 0.03)

    def feedback_penalty(self, confidence: float) -> float:
        """Bounded feedback: -0.05, floor 0.1"""
        return max(0.1, confidence - 0.05)

    def should_archive(self, confidence: float) -> bool:
        return confidence < self._config.prune_threshold

    def should_tombstone(self, confidence: float) -> bool:
        return confidence < self._config.tombstone_threshold
