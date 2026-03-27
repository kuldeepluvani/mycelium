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
from mycelium.perception.entity_resolver import EntityResolver
from mycelium.perception.relationship_builder import RelationshipBuilder
from mycelium.network.cluster import ClusterEngine
from mycelium.network.agent_manager import AgentManager
from mycelium.network.spillover import SpilloverEngine
from mycelium.network.agent import Agent
from mycelium.observe.store import ObservationStore
from mycelium.serve.feedback import FeedbackLoop


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

        # Network — adaptive thresholds based on graph size
        # For smaller graphs (<200 nodes), relax thresholds to allow discovery
        # Lower thresholds for smaller graphs to maximize node coverage
        node_count = 0  # unknown at init, will be set after rebuild
        adaptive_min_size = max(3, config.network.min_cluster_size // 3)
        adaptive_coherence = min(config.network.min_coherence, 0.1)
        self.cluster_engine = ClusterEngine(
            min_cluster_size=adaptive_min_size,
            min_coherence=adaptive_coherence,
            max_inter_density=config.network.max_inter_density,
        )
        self.agent_manager = AgentManager(
            llm=self._llm,
            stability_cycles=1,  # Activate on first qualifying cycle (persisted state handles multi-run stability)
        )
        self.spillover = SpilloverEngine(
            llm=self._llm,
            edge_threshold=config.network.spillover_edge_threshold,
        )

        # Session
        obs_db_path = config.data_dir / "observation.db"
        self.session_store = SessionStore(str(obs_db_path))
        self.observation_store = ObservationStore(obs_db_path)

        # Clean up all stale "running" sessions from previous crashes
        for s in self.session_store.list_sessions():
            if s.status == "running":
                s.status = "interrupted"
                s.completed_at = datetime.now(timezone.utc)
                self.session_store.save(s)

        # Rebuild graph and agents from store
        self._rebuild_graph()
        self._load_agents()

        # Load persisted L2 meta-agents
        persisted_metas = self.store.load_meta_agents()
        if persisted_metas:
            self.agent_manager._meta_agents = {m.id: m for m in persisted_metas}
            for meta in persisted_metas:
                for child in meta.children:
                    agent = self.agent_manager.get(child.agent_id)
                    if agent:
                        agent.parent_id = meta.id

        # Ensure all entities have agent coverage
        self.agent_manager.ensure_catchall(self.graph)

    def _rebuild_graph(self):
        """Rebuild NetworkX graph from SQLite."""
        rows = self.store.execute(
            "SELECT id FROM entities WHERE archived = 0"
        ).fetchall()
        for row in rows:
            entity = self.store.get_entity(row[0])
            if entity:
                self.graph.add_entity(entity)

        rows = self.store.execute(
            "SELECT id FROM relationships WHERE archived = 0"
        ).fetchall()
        for row in rows:
            rel = self.store.get_relationship(row[0])
            if rel and self.graph.has_entity(rel.source_id) and self.graph.has_entity(rel.target_id):
                self.graph.add_relationship(rel)

    def _load_agents(self):
        """Load persisted agents from SQLite."""
        import json
        rows = self.store.execute(
            "SELECT id, name, domain, description, seed_nodes, status, "
            "queries_answered, avg_confidence, discovered_at, last_active, pinned "
            "FROM agents WHERE status != 'retired'"
        ).fetchall()
        for row in rows:
            agent = Agent(
                id=row[0], name=row[1], domain=row[2],
                description=row[3] or "",
                seed_nodes=json.loads(row[4]) if row[4] else [],
                status=row[5],
                queries_answered=row[6] or 0,
                avg_confidence=row[7] or 0.0,
                pinned=bool(row[10]),
            )
            # Load node membership
            node_rows = self.store.execute(
                "SELECT entity_id FROM agent_nodes WHERE agent_id = ?", (agent.id,)
            ).fetchall()
            agent.node_ids = [r[0] for r in node_rows]
            self.agent_manager._agents[agent.id] = agent

    def _save_agents(self):
        """Persist agents to SQLite."""
        import json
        for agent in self.agent_manager.agents:
            self.store.execute(
                "INSERT OR REPLACE INTO agents "
                "(id, name, domain, description, seed_nodes, status, "
                "queries_answered, avg_confidence, discovered_at, last_active, pinned) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (agent.id, agent.name, agent.domain, agent.description,
                 json.dumps(agent.seed_nodes), agent.status,
                 agent.queries_answered, agent.avg_confidence,
                 agent.discovered_at.isoformat(),
                 agent.last_active.isoformat() if agent.last_active else None,
                 int(agent.pinned)),
            )
            # Save node membership
            self.store.execute("DELETE FROM agent_nodes WHERE agent_id = ?", (agent.id,))
            for node_id in agent.node_ids:
                self.store.execute(
                    "INSERT OR IGNORE INTO agent_nodes (agent_id, entity_id, cycle_assigned) VALUES (?, ?, 1)",
                    (agent.id, node_id),
                )
            self.store.conn.commit()

        # Save L2 meta-agents — clear old ones first to prevent duplicates
        self.store.execute("DELETE FROM meta_agent_children")
        self.store.execute("DELETE FROM meta_agents")
        self.store.conn.commit()
        for meta in self.agent_manager.get_meta_agents():
            self.store.upsert_meta_agent(meta)

    async def learn(self, budget: int = 50, force: bool = False) -> LearnSession:
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
                changes = await connector.discover_changes(known_hashes=self.store, force=force)
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

            # Save content hashes for processed documents
            for doc in docs_to_process:
                self.store.save_document_hash(doc.path, doc.content_hash)

        # Apply confidence decay to all entities
        for eid in self.graph.all_entity_ids():
            entity = self.graph.get_entity(eid)
            if entity and not entity.quarantined and not entity.archived:
                new_conf = self.decay.apply_decay(entity.confidence, "semantic")
                entity.confidence = new_conf
                self.store.update_entity_confidence(eid, new_conf)

        # Apply confidence decay to all relationships
        for rel in self.graph.all_relationships():
            if not rel.quarantined and not rel.archived:
                new_conf = self.decay.apply_decay(rel.confidence, rel.rel_category)
                rel.confidence = new_conf
                self.store.update_relationship_confidence(rel.id, new_conf)

        # Apply pending user feedback (boosts/penalties)
        feedback = FeedbackLoop(store=self.store)
        applied = feedback.apply_pending(self.store, self.graph, self.decay)

        # Batch dedup pass — merge duplicate entities
        resolver = EntityResolver(self.graph, self.embeddings, self._llm)
        merge_pairs = resolver.batch_find_duplicates()
        for keep_id, remove_id in merge_pairs:
            resolver.merge_entities(keep_id, remove_id, store=self.store)

        # Cross-document relationship enrichment
        if quota.can_spend(5):
            enricher = RelationshipBuilder(
                self._llm, batch_size=self.config.perception.batch_size_relationships
            )
            new_edges = await enricher.enrich_cross_document(
                self.graph, self.store, budget=3
            )
            session.edges_created += new_edges

        # Agent discovery (if graph big enough)
        if self.graph.node_count() >= self.config.network.min_graph_nodes_for_discovery:
            clusters = self.cluster_engine.detect(self.graph)
            new_agents = await self.agent_manager.process_clusters(clusters, self.graph)
            session.agents_discovered = len(new_agents)

            # Ensure catch-all agent covers remaining orphan entities
            self.agent_manager.ensure_catchall(self.graph)

            # Spillover
            if quota.can_spend(len(self.agent_manager.get_active())):
                results = await self.spillover.analyze_all_pairs(
                    self.agent_manager.get_active(), self.graph
                )
                for r in results:
                    session.spillovers += len(r.new_relationships)

            # Cache L2 spillover results for API
            import json as json_mod
            metas = self.agent_manager.get_meta_agents()
            if len(metas) >= 2:
                l2_results = await self.spillover.analyze_meta_pairs(
                    metas, self.agent_manager.get_active(), self.graph
                )
                # Clear old cache and store new
                self.store.execute("DELETE FROM spillover_cache")
                active_metas = [m for m in metas if m.status == "active"]
                idx = 0
                for i, meta_a in enumerate(active_metas):
                    for meta_b in active_metas[i + 1:]:
                        if idx < len(l2_results) and not l2_results[idx].skipped:
                            self.store.execute(
                                "INSERT INTO spillover_cache "
                                "(meta_a_id, meta_a_name, meta_b_id, meta_b_name, relationships, computed_at) "
                                "VALUES (?, ?, ?, ?, ?, ?)",
                                (meta_a.id, meta_a.name, meta_b.id, meta_b.name,
                                 json_mod.dumps([
                                     {"source": r.source_id, "target": r.target_id,
                                      "rel_type": r.rel_type, "rationale": r.rationale}
                                     for r in l2_results[idx].new_relationships
                                 ]),
                                 datetime.now(timezone.utc).isoformat()),
                            )
                        idx += 1
                self.store.conn.commit()

        # Save embeddings and agents
        self.embeddings.save()
        self._save_agents()

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
