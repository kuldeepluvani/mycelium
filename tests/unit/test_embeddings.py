import pytest
from mycelium.brainstem.embeddings import EmbeddingIndex


@pytest.fixture
def index(tmp_path):
    return EmbeddingIndex(index_path=tmp_path / "test.faiss", model_name="all-MiniLM-L6-v2")


def test_add_and_search(index):
    index.add("e1", "Kubernetes container orchestration platform")
    index.add("e2", "PostgreSQL relational database")
    index.add("e3", "GKE Google Kubernetes Engine")
    results = index.search("k8s container", top_k=2)
    assert len(results) == 2
    ids = [r.entity_id for r in results]
    assert "e1" in ids or "e3" in ids


def test_save_and_load(index, tmp_path):
    index.add("e1", "test embedding content")
    index.save()
    loaded = EmbeddingIndex(index_path=tmp_path / "test.faiss", model_name="all-MiniLM-L6-v2")
    loaded.load()
    results = loaded.search("test", top_k=1)
    assert len(results) == 1
    assert results[0].entity_id == "e1"


def test_empty_index_search(index):
    results = index.search("anything", top_k=5)
    assert results == []


def test_count(index):
    assert index.count == 0
    index.add("e1", "test")
    assert index.count == 1
