import pytest
from mycelium.brainstem.decay import DecayEngine
from mycelium.shared.config import DecayConfig


@pytest.fixture
def engine():
    return DecayEngine(DecayConfig())


def test_apply_decay_structural(engine):
    new = engine.apply_decay(0.5, "structural")
    assert new == pytest.approx(0.49, abs=0.001)


def test_apply_decay_temporal(engine):
    new = engine.apply_decay(0.5, "temporal")
    assert new == pytest.approx(0.425, abs=0.001)


def test_apply_decay_unknown_category(engine):
    new = engine.apply_decay(0.5, "unknown")
    assert new == pytest.approx(0.475, abs=0.001)


def test_boost(engine):
    assert engine.boost(0.5) == pytest.approx(0.55)
    assert engine.boost(0.96) == 0.99  # capped


def test_feedback_boost(engine):
    assert engine.feedback_boost(0.5) == pytest.approx(0.53)
    assert engine.feedback_boost(0.97) == 0.99  # capped


def test_feedback_penalty(engine):
    assert engine.feedback_penalty(0.5) == pytest.approx(0.45)
    assert engine.feedback_penalty(0.12) == 0.1  # floored


def test_should_archive(engine):
    assert engine.should_archive(0.09) is True
    assert engine.should_archive(0.11) is False


def test_should_tombstone(engine):
    assert engine.should_tombstone(0.04) is True
    assert engine.should_tombstone(0.06) is False
