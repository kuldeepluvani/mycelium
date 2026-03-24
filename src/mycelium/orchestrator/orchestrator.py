"""Orchestrator — coordinates learn cycles and serve mode."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from mycelium.shared.config import MyceliumConfig
from mycelium.shared.llm import ClaudeCLI
from mycelium.brainstem.store import BrainstemStore
from mycelium.brainstem.graph import KnowledgeGraph
from mycelium.brainstem.embeddings import EmbeddingIndex
from mycelium.brainstem.decay import DecayEngine
from mycelium.connectors.vault import VaultConnector
from mycelium.connectors.git import GitConnector
from mycelium.connectors.registry import ConnectorRegistry
from mycelium.orchestrator.quota import QuotaTracker
from mycelium.orchestrator.priority import PriorityScorer
from mycelium.orchestrator.session import SessionStore, LearnSession
from mycelium.perception.engine import PerceptionEngine
from mycelium.network.cluster import ClusterEngine
from mycelium.network.agent_manager import AgentManager
from mycelium.network.spillover import SpilloverEngine
from mycelium.observe.store import ObservationStore


class Orchestrator:
    def __init__(self, config: MyceliumConfig):
        self.config = config
        self._llm = ClaudeCLI()

        # Brainstem
        db_path = config.data_dir / "brainstem.db"
        self.store = BrainstemStore(db_path)
        self.store.initialize()
        self.graph = KnowledgeGraph()
        self.embeddings = EmbeddingIndex(
            index_path=config.data_dir / "embeddings.faiss",
            model_name="all-MiniLM-L6-v2",
        )
        if (config.data_dir / "embeddings.faiss").exists():
            self.embeddings.load()
        self.decay = DecayEngine(config.brainstem.decay)

        # Connectors
        self.connector_registry = ConnectorRegistry()
        if config.connectors.vault.enabled and config.connectors.vault.path:
            self.connector_registry.register(VaultConnector(
                vault_path=config.connectors.vault.path,
                extensions=config.connectors.vault.extensions,
                ignore_patterns=config.connectors.vault.ignore_patterns,
            ))
        if config.connectors.git.enabled and config.connectors.git.base_path:
            self.connector_registry.register(GitConnector(
                base_path=config.connectors.git.base_path,
                include_repos=config.connectors.git.include_repos,
                exclude_repos=config.connectors.git.exclude_repos,
                max_repos_per_cycle=config.connectors.git.max_repos_per_cycle,
                commit_lookback_days=config.connectors.git.commit_lookback_days,
                extract_commits=config.connectors.git.extract_commits,
                extract_readme=config.connectors.git.extract_readme,
                extract_structure=config.connectors.git.extract_structure,
            ))

        # Perception
        self.perception = PerceptionEngine(
            llm=self._llm,
            graph=self.graph,
            store=self.store,
            embeddings=self.embeddings,
            config=config.perception,
        )

        # Network
        self.cluster_engine = ClusterEngine(
            min_cluster_size=config.network.min_cluster_size,
            min_coherence=config.network.min_coherence,
            max_inter_density=config.network.max_inter_density,
        )
        self.agent_manager = AgentManager(
            llm=self._llm,
            stability_cycles=config.network.stability_cycles,
        )
        self.spillover = SpilloverEngine(
            llm=self._llm,
            edge_threshold=config.network.spillover_edge_threshold,
        )

        # Session
        obs_db_path = config.data_dir / "observation.db"
        self.session_store = SessionStore(str(obs_db_path))
        self.observation_store = ObservationStore(obs_db_path)

        # Rebuild graph from store
        self._rebuild_graph()

    def _rebuild_graph(self):
        """Rebuild NetworkX graph from SQLite."""
        # Load all non-archived entities
        rows = self.store.execute(
            "SELECT id FROM entities WHERE archived = 0"
        ).fetchall()
        for row in rows:
            entity = self.store.get_entity(row[0])
            if entity:
                self.graph.add_entity(entity)

        # Load all non-archived relationships
        rows = self.store.execute(
            "SELECT id FROM relationships WHERE archived = 0"
        ).fetchall()
        for row in rows:
            rel = self.store.get_relationship(row[0])
            if rel and self.graph.has_entity(rel.source_id) and self.graph.has_entity(rel.target_id):
                self.graph.add_relationship(rel)

    async def learn(self, budget: int = 50) -> LearnSession:
        """Run a learn cycle with the given call budget."""
        session = LearnSession(budget=budget)
        self.session_store.save(session)

        quota = QuotaTracker(budget)
        scorer = PriorityScorer()
        is_first = self.graph.node_count() == 0

        # Discover changes from all connectors
        all_changesets = []
        for connector in self.connector_registry.all():
            try:
                changes = await connector.discover_changes()
                all_changesets.extend(changes)
            except Exception as e:
                session.documents_remaining.append(f"error:{connector.source_type()}:{e}")

        # Rank and allocate budget
        ranked = scorer.rank(all_changesets)
        tier_budget = scorer.allocate_budget(budget)

        # Process documents within budget
        docs_to_process = []
        for item in ranked[:tier_budget["changed"]]:
            if not quota.can_spend(3):  # ~3 calls per doc
                break
            connector = self.connector_registry.get(item.changeset.source)
            if connector:
                try:
                    doc = await connector.fetch_content(item.changeset.path)
                    if doc:
                        docs_to_process.append(doc)
                except Exception:
                    continue

        # Run perception engine
        if docs_to_process:
            stats = await self.perception.process_batch(
                docs_to_process,
                is_first_cycle=is_first,
                max_concurrent=self.config.perception.max_concurrent_pipelines,
            )
            session.entities_created = stats.entities_created
            session.edges_created = stats.relationships_created
            session.documents_processed = [d.path for d in docs_to_process]
            session.spent = stats.total_call_cost

        # Agent discovery (if graph big enough)
        if self.graph.node_count() >= self.config.network.min_graph_nodes_for_discovery:
            clusters = self.cluster_engine.detect(self.graph)
            new_agents = await self.agent_manager.process_clusters(clusters, self.graph)
            session.agents_discovered = len(new_agents)

            # Spillover
            if quota.can_spend(len(self.agent_manager.get_active())):
                results = await self.spillover.analyze_all_pairs(
                    self.agent_manager.get_active(), self.graph
                )
                for r in results:
                    session.spillovers += len(r.new_relationships)

        # Save embeddings
        self.embeddings.save()

        # Complete session
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
        self.session_store.save(session)

        # Checkpoint
        self.store.checkpoint()

        return session

    def status(self) -> dict:
        """Get current system status."""
        latest = self.session_store.get_latest()
        return {
            "graph": {
                "nodes": self.graph.node_count(),
                "edges": self.graph.edge_count(),
            },
            "agents": {
                "total": len(self.agent_manager.agents),
                "active": len(self.agent_manager.get_active()),
            },
            "last_session": {
                "id": latest.id if latest else None,
                "status": latest.status if latest else None,
                "entities_created": latest.entities_created if latest else 0,
            },
            "connectors": self.connector_registry.source_types(),
        }
