"""Tests for semantic intent parsing via embeddings fallback."""
from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from mycelium.shared.models import Entity
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.serve.intent import IntentParser


@pytest.fixture
def graph():
    g = KnowledgeGraph()
    g.add_entity(Entity(id="e1", name="Redis", canonical_name="Redis",
                       entity_class="infra", description="In-memory data store"))
    g.add_entity(Entity(id="e2", name="AuthService", canonical_name="AuthService",
                       entity_class="service", description="Authentication service"))
    return g


def test_exact_match_still_works(graph):
    parser = IntentParser(graph)
    intent = parser.parse("Tell me about Redis")
    assert "e1" in intent.mentioned_entities


def test_case_insensitive_match(graph):
    parser = IntentParser(graph)
    intent = parser.parse("how does redis work?")
    assert "e1" in intent.mentioned_entities


def test_semantic_match_with_embeddings(graph):
    """When embeddings are available, fuzzy matches should find related entities."""
    mock_embeddings = MagicMock()
    mock_result = MagicMock()
    mock_result.entity_id = "e1"
    mock_result.score = 0.75
    mock_embeddings.search.return_value = [mock_result]
    mock_embeddings.count = 2

    parser = IntentParser(graph, embeddings=mock_embeddings, semantic_threshold=0.6)
    # Query doesn't mention "Redis" by name
    intent = parser.parse("what is the caching layer?")
    assert "e1" in intent.mentioned_entities
    mock_embeddings.search.assert_called_once()


def test_semantic_below_threshold_ignored(graph):
    """Results below the threshold should not be included."""
    mock_embeddings = MagicMock()
    mock_result = MagicMock()
    mock_result.entity_id = "e1"
    mock_result.score = 0.4  # below default 0.6 threshold
    mock_embeddings.search.return_value = [mock_result]
    mock_embeddings.count = 2

    parser = IntentParser(graph, embeddings=mock_embeddings, semantic_threshold=0.6)
    intent = parser.parse("what is the caching layer?")
    assert "e1" not in intent.mentioned_entities


def test_semantic_skipped_when_string_match_sufficient(graph):
    """If string matching already found 3+ entities, skip semantic search."""
    graph.add_entity(Entity(id="e3", name="redis-cluster", canonical_name="redis-cluster",
                           entity_class="infra"))
    graph.add_entity(Entity(id="e4", name="redis-sentinel", canonical_name="redis-sentinel",
                           entity_class="infra"))

    mock_embeddings = MagicMock()
    mock_embeddings.count = 2

    parser = IntentParser(graph, embeddings=mock_embeddings)
    intent = parser.parse("redis redis-cluster redis-sentinel setup")
    mock_embeddings.search.assert_not_called()


def test_no_embeddings_graceful(graph):
    """Without embeddings, parser should work normally (string matching only)."""
    parser = IntentParser(graph, embeddings=None)
    intent = parser.parse("what is the caching layer?")
    assert isinstance(intent.mentioned_entities, list)
    assert len(intent.mentioned_entities) == 0


def test_semantic_no_duplicate_with_string_match(graph):
    """If string matching already found an entity, semantic should not add it again."""
    mock_embeddings = MagicMock()
    mock_result = MagicMock()
    mock_result.entity_id = "e1"
    mock_result.score = 0.9
    mock_embeddings.search.return_value = [mock_result]
    mock_embeddings.count = 2

    parser = IntentParser(graph, embeddings=mock_embeddings)
    # "Redis" will be found by string matching, then embedding also returns e1
    intent = parser.parse("Tell me about Redis")
    assert intent.mentioned_entities.count("e1") == 1


def test_semantic_skips_unknown_entity(graph):
    """If embedding returns an entity_id not in the graph, skip it."""
    mock_embeddings = MagicMock()
    mock_result = MagicMock()
    mock_result.entity_id = "e_unknown"
    mock_result.score = 0.9
    mock_embeddings.search.return_value = [mock_result]
    mock_embeddings.count = 2

    parser = IntentParser(graph, embeddings=mock_embeddings)
    intent = parser.parse("what is the caching layer?")
    assert "e_unknown" not in intent.mentioned_entities


def test_semantic_exception_handled_gracefully(graph):
    """If embeddings.search raises, parser should not crash."""
    mock_embeddings = MagicMock()
    mock_embeddings.count = 2
    mock_embeddings.search.side_effect = RuntimeError("FAISS error")

    parser = IntentParser(graph, embeddings=mock_embeddings)
    intent = parser.parse("what is the caching layer?")
    assert isinstance(intent.mentioned_entities, list)
