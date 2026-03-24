# Mycelium — Self-Enriching Knowledge Engine

> "A living knowledge network that learns while you sleep and thinks while you work."

## Overview

Mycelium is a local-first knowledge engine that ingests data from Obsidian vaults and Git repositories, builds a living knowledge graph with rationale on every connection, auto-discovers specialist agents from data clusters, shares knowledge across agent domains via spillover, and answers questions with full cognition — traceable rationale chains backed by evidence.

It operates in two modes: **Learn** (background enrichment using remaining Claude CLI quota) and **Serve** (query with full graph cognition). A persistent observation layer provides real-time visibility into all processes.

## Architecture

```
CLI / Skill
  mycelium init | learn --calls 50 | serve | ask | observe
                            |
                            v
                      NATS JetStream
          (auto-managed, persistent, replayable)

  Subjects: mycelium.connector.>  mycelium.perception.>
            mycelium.graph.>      mycelium.network.>
            mycelium.orchestrator.> mycelium.serve.>
            mycelium.system.>

   |          |           |          |          |          |
   v          v           v          v          v          v
Orchest-  Connect-   Percep-   Brain-   Mycelial  Observe
rator     ors        tion      stem     Network

Modes     Vault      5-layer   Graph    Louvain   Sub ALL
Quota     Git        verify    SQLite   Agents    Persist
Priority  (Jira)     pipeline  FAISS    Spillovr  TUI
Session   (Conf)               Search   Gap det   REST
```

### Design Principles

1. **Event-driven** — All modules communicate through NATS JetStream. No direct module-to-module calls.
2. **SQLite as source of truth** — NetworkX is compute layer, SQLite is persistence. Crash recovery rebuilds from SQLite.
3. **Open taxonomy** — Entity types and relationship types are open strings, not fixed enums. New domains create new types automatically.
4. **Break-proof** — 5-layer adversarial verification, contradiction-aware graph, anomaly detection, quarantine for suspicious data.
5. **Budget-aware** — Every Claude CLI call is tracked. Learn cycles operate within a fixed call budget.
6. **Observable** — Every event persisted. Live TUI, REST API, and CLI snapshot interfaces.

---

## 1. Event Bus (NATS JetStream)

### Why NATS

- Free, open source (Apache 2.0), single binary
- 10M+ msg/sec throughput
- JetStream provides: persistence, replay, exactly-once delivery, dead letter queue
- Python async client (`nats-py`) is production-grade
- Scales from local Mac to distributed cluster with zero code changes

### Subject Hierarchy

```
mycelium.connector.>          # DocumentIngested, DocumentChanged
mycelium.perception.>         # EntitiesExtracted, RelationshipBuilt, ConceptFormed
mycelium.graph.>              # GraphUpdated
mycelium.network.>            # ClusterDetected, AgentDiscovered, SpilloverTriggered
mycelium.orchestrator.>       # LearnCycleStarted, CallSpent, QuotaExhausted
mycelium.serve.>              # QueryReceived, QueryRouted, QueryAnswered
mycelium.system.>             # ErrorOccurred, HealthCheck
```

### Event Types

```python
# Connector events
DocumentIngested(source, path, content_hash, timestamp)
DocumentChanged(source, path, diff_summary, timestamp)
DocumentDeleted(source, path, orphaned_entity_ids: list[str])

# Perception events
EntitiesExtracted(node_id, entities: list[Entity], call_cost: int)
RelationshipBuilt(source_id, target_id, rel_type, rationale, confidence)
ConceptFormed(concept_id, member_nodes, label, description)
EntityMerged(source_id, target_id, surviving_id, merge_reason)
DataQuarantined(entity_ids: list[str], reason: str, layer: int)

# Graph events
GraphUpdated(node_ids: list[str], edge_count_delta: int)

# Network events
ClusterDetected(cluster_id, node_ids, coherence_score)
AgentDiscovered(agent_id, domain, seed_nodes)
AgentRetired(agent_id, reason)
SpilloverTriggered(from_agent, to_agent, shared_edges)

# Orchestration events
LearnCycleStarted(budget: int, priority_queue: list)
CallSpent(call_number: int, budget_remaining: int, task_type: str)
QuotaExhausted(total_spent: int, tasks_completed: int)
LearnCycleCompleted(stats: LearnStats)

# Serve events
QueryReceived(query: str, session_id: str)
QueryRouted(query: str, agents: list[str], rationale: str)
QueryAnswered(query: str, response: str, sources: list)

# System events
ErrorOccurred(module: str, error: str, recoverable: bool)
HealthCheck(module: str, status: str, metrics: dict)
```

### Bus Properties

- **Async** — `asyncio` based, non-blocking publish/subscribe
- **Typed** — Events are Pydantic models with validation
- **Ordered** — Events within a subject maintain insertion order
- **Persistent** — JetStream stores events for replay and debugging
- **Dead letter queue** — Failed handlers don't crash the bus
- **Backpressure** — Bounded queue per subscriber (configurable, default 1024)

---

## 2. Connectors (Data Sources)

### Base Interface

```python
class BaseConnector:
    async def discover_changes(self, since: datetime) -> list[ChangeSet]
    async def fetch_content(self, path: str) -> Document
    def source_type(self) -> str  # "vault", "git"
```

### Vault Connector (Obsidian)

- Watches vault directory for `.md` files
- Parses YAML frontmatter as structured metadata
- Extracts `[[wikilinks]]` as pre-existing relationships
- Change detection: file mtime comparison against last learn cycle
- Ignores: `.obsidian/*`, `.trash/*`

### Git Connector

- Scans repos in `Github/` directory
- Extracts per repo: README/docs, recent commits (`git log --since`), file structure, PR descriptions (via `gh` CLI)
- Change detection: `git log --since="last learn"` per repo
- Config: `max_repos_per_cycle = 10`, most-recently-modified first
- Progressive coverage across multiple learn cycles

### Connector Registry

- Connectors self-register on startup
- Adding a new connector = one file implementing `BaseConnector` + register on bus
- No core code changes needed

---

## 3. Perception Layer (5-Layer Verification Pipeline)

### Pipeline

```
DocumentIngested
  |
  v
  Layer 1: STRUCTURAL PRE-PARSE (0 Claude calls)
    Regex + spaCy extracts ground truth entities:
    - Code: function names, imports, classes
    - Markdown: headers, frontmatter, wikilinks, URLs
    - Git: commit authors, file paths, branches
    - Temporal: dates, deadlines, versions
  |
  v
  Layer 2: DEEP EXTRACT (1 Claude call)
    LLM receives document + Layer 1 anchors
    Fills gaps — semantic entities, claims, relationships
    Anchored to ground truth = fewer hallucinations
  |
  v
  Layer 3: ADVERSARIAL CHALLENGE (0-1 Claude call)
    Independent Claude call reviews Layer 2 output
    Rates each extraction: CONFIRMED / UNCERTAIN / REJECT
    Skipped if Layer 1 found >80% of entities (configurable)
  |
  v
  Layer 4: GRAPH CONSISTENCY CHECK (0 Claude calls)
    Algorithmic checks against existing graph:
    - Contradiction detection
    - Temporal consistency
    - Degree anomaly detection
    - Cluster coherence
  |
  v
  Layer 5: RECONCILIATION (0-1 Claude call)
    Only fires on conflicts between layers or graph contradictions
    If still ambiguous → QUARANTINE (stored separately, not in active graph)
```

### Accuracy Mechanisms

| Mechanism | Purpose |
|:--|:--|
| Layer 1 anchors | Reduces hallucination ~40% by grounding LLM in facts |
| Adversarial challenge | Independent verification catches remaining errors |
| Graph consistency | Catches temporal paradoxes, statistical outliers |
| Quarantine | Suspicious data isolated, not admitted to graph |
| Anomaly detection | >50 entities or >100 edges from one doc → quarantine |

### Performance Mechanisms

| Mechanism | Savings |
|:--|:--|
| Layer 1 pre-parse | ~30% fewer extraction calls |
| Batch relationship building | 15 pairs per call (~60% savings) |
| Batch entity resolution | 10 matches per call (~50% savings) |
| Skip-if-unchanged | 100% savings for unchanged docs |
| Incremental extraction | ~70% savings for modified docs |
| Challenge skip (high-anchor) | ~40% fewer challenge calls |
| 3 parallel pipelines | 3x wall-clock improvement |

### Call Budget

Average ~2.2 calls per document. 50-call budget = ~22 documents per learn cycle.

### Entity Model (Open Taxonomy)

```python
class Entity:
    id: str
    name: str
    canonical_name: str          # resolved ("k8s" -> "Kubernetes")
    entity_class: str            # broad: "technology", "person", "concept"
    entity_subclass: str         # specific: "container_orchestrator", "CEO"
    domain: str                  # auto-detected: "infrastructure", "finance"
    aliases: list[str]
    description: str
    properties: dict[str, Any]   # open schema
    provenance: list[str]        # source document IDs
    confidence: float
    first_seen: datetime
    last_seen: datetime
    version: int
```

### Relationship Model

```python
class Relationship:
    source_id: str
    target_id: str
    rel_type: str                # open-ended
    rel_category: str            # causal, structural, temporal, semantic
    rationale: str               # WHY this connection exists
    evidence: list[Evidence]     # source quotes
    confidence: float
    strength: float
    bidirectional: bool
    temporal_scope: TimeScope    # when is this valid?
    contradiction_of: str | None
    decay_rate: float
    version: int
    created_at: datetime
    last_validated: datetime

class Evidence:
    document_id: str
    quote: str
    location: str
    extracted_at: datetime

class TimeScope:
    valid_from: datetime | None
    valid_until: datetime | None
    is_permanent: bool
```

### Entity Resolver (Deduplication)

Multi-signal resolution pipeline:
1. Exact name match
2. Alias match
3. Embedding similarity (FAISS, cosine < 0.15)
4. Co-occurrence analysis
5. Domain match boost
6. LLM arbitration for ambiguous cases (batched, 10 per call)

On first run (empty FAISS): falls back to name/alias matching only.

### Concept Formation

When 5+ entities form a highly interconnected cluster with shared context, Perception synthesizes a concept node — a higher-order abstraction that doesn't exist in any single document.

---

## 4. Brainstem (Knowledge Graph + Storage)

### Components

- **Graph**: NetworkX in-memory for fast traversal + algorithms
- **Store**: SQLite on disk as source of truth (transactions, crash recovery)
- **Embeddings**: FAISS for vector similarity search, sentence-transformers for local embedding generation
- **Search**: Hybrid — graph traversal + vector similarity + keyword
- **Cache**: Hot cache for frequently accessed subgraphs
- **Decay**: Confidence lifecycle management

### Sync Protocol

1. On startup: rebuild NetworkX from SQLite
2. On write: SQLite transaction first, then NetworkX update
3. On crash: SQLite is authoritative, NetworkX rebuilt

### Confidence & Decay System

```
Birth:       confidence = Layer 2 score x Layer 3 modifier

Growth:      each cycle that re-confirms
             confidence += 0.05 (cap 0.99)
             last_validated = now

Decay:       each cycle that does NOT re-encounter
             confidence *= (1 - decay_rate)
             Default rates by rel_category:
               structural:   0.02/cycle (slow — dependencies, ownership)
               causal:       0.05/cycle (medium — cause/effect)
               semantic:     0.10/cycle (fast — weak associations)
               temporal:     0.15/cycle (fastest — time-bound facts)

Pruning:     confidence < 0.1  -> archived (cold store)
             confidence < 0.05 -> tombstoned (record kept)

Resurrection: tombstoned entity reappears -> restored with fresh confidence
```

### Contradiction Handling

Contradictions are first-class edges, not hidden:

```
Existing: zauthz --[DEPENDS_ON]--> GCP IAM (0.85)
New:      zauthz --[DEPENDS_ON]--> AWS IAM (0.78)

Both stored. Meta-edge: Edge1 --[CONTRADICTS]--> Edge2
Agents see both sides. Human or evidence resolves.
```

---

## 5. Mycelial Network (Agent Discovery + Spillover)

### Agent Discovery

After each learn cycle:
1. Louvain community detection on knowledge graph
2. Each cluster evaluated: size (min 10 nodes), coherence (>0.3), distinctness (<0.15 inter-density), stability (2+ cycles)
3. Qualifying clusters → 1 Claude CLI call per new agent to generate: name, description, expertise, question types
4. Minimum 50 graph nodes before first discovery attempt

### Agent Lifecycle

```
CANDIDATE -> ACTIVE -> MATURE -> RETIRED

CANDIDATE: Cluster detected, not yet stable (< 2 cycles)
ACTIVE:    Stable cluster, agent formed, serving queries
MATURE:    10+ queries answered, avg confidence > 0.7
RETIRED:   Cluster dissolved or merged. Knowledge preserved.
```

### User Override

```bash
mycelium agents list
mycelium agents merge agent-1 agent-2
mycelium agents split platform --by tag
mycelium agents rename agent-1 "K8s Ops"
mycelium agents pin "K8s Ops"           # prevent auto-retirement
mycelium agents create --seed "node1,node2,node3"
```

### Spillover (Cross-Domain Knowledge Transfer)

For each agent pair with 5+ inter-cluster edges:
1. Summarize each agent's domain subgraph
2. One Claude CLI call: identify missing connections, risks at boundary, knowledge gaps
3. New cross-domain edges created with `SpilloverType`

Spillover types:
- `DEPENDENCY_CHAIN` — A depends on something B owns
- `SHARED_CONCEPT` — Both domains use same concept differently
- `CAUSAL_BRIDGE` — Action in A causes effect in B
- `RISK_PROPAGATION` — Failure in A cascades to B
- `KNOWLEDGE_GAP` — A has context B needs

---

## 6. Orchestrator

### Modes

- **IDLE** — Default. No activity.
- **LEARN** — Active enrichment cycle. Budget-aware. Serve operates in read-only mode during learn (queries use graph snapshot from cycle start).
- **SERVE** — Query mode. API + WebSocket active. Full read-write feedback loop.

Serve and Learn can co-exist: during learn, serve runs read-only against a graph snapshot taken at cycle start. SQLite WAL mode supports concurrent readers with a single writer. NetworkX graph is snapshotted (shallow copy) at learn cycle start for serve queries. Feedback loop confidence adjustments are queued and applied after learn cycle completes.

### Priority Queue

Documents ranked by composite score:

| Factor | Weight | Description |
|:--|:--|:--|
| Recency | 0.30 | Newer changes score higher |
| Connectivity | 0.25 | Docs connected to many nodes = high impact |
| Staleness | 0.20 | Nodes not validated recently |
| Source trust | 0.15 | Vault > git commit messages |
| Change magnitude | 0.10 | Large diffs > typo fixes |

### Budget Allocation Per Cycle

| Tier | Budget % | Purpose |
|:--|:--|:--|
| Tier 1: CHANGED | 60% | New/modified documents |
| Tier 2: STALE | 25% | Re-validate decayed nodes |
| Tier 3: CROSS-LINK | 15% | Spillover + concept formation |

### Quota Tracker

Every Claude CLI call logged:
- Call number, timestamp, task type, module, estimated tokens, duration, success
- `can_spend(n)` — check budget
- `spend(record)` — log and publish `CallSpent`
- `QuotaExhausted` triggers graceful drain of all pipelines

### Graceful Shutdown

1. Perception: finish current document, don't start new
2. Relationship builder: flush current batch
3. Spillover: cancel if mid-call, complete if near-done
4. Graph: commit all pending writes (atomic SQLite transaction)
5. Observation: log final stats
6. Publish `LearnCycleCompleted`

No data lost. Next cycle resumes from checkpoint.

### Crash Recovery

`LearnSession` persisted to SQLite:
- Tracks: documents processed, documents remaining, last checkpoint
- On restart: skip processed docs, resume from checkpoint
- Staging tables for in-progress extractions cleared on restart

---

## 7. Serve Mode (Query Pipeline)

### Pipeline

```
Query received
  |
  v
  Stage 1: INTENT PARSE (0 Claude calls)
    Extract mentioned entities, classify query type,
    identify temporal scope, pull subgraph (3 hops)
  |
  v
  Stage 2: AGENT SELECTION (0 Claude calls)
    Rank agents by owned_nodes_in_subgraph / total_subgraph_nodes
    Select top 3 agents
    Include spillover edges between selected agents
  |
  v
  Stage 3: PARALLEL AGENT REASONING (1-3 Claude calls)
    Each agent receives: query + domain subgraph + spillover context
    Runs in parallel (concurrent Claude CLI subprocesses)
  |
  v
  Stage 4: SYNTHESIS (1 Claude call)
    Combines all agent responses
    Produces: unified answer, confidence per claim, sources cited,
              unknowns, suggested follow-ups
  |
  v
  Stage 5: FEEDBACK LOOP (0 Claude calls)
    User acceptance -> confidence boost to cited edges
    User correction -> confidence penalty
    Published as events, observation layer logs
```

### Rationale Chain

Every answer includes traceable reasoning:
- Each claim linked to specific graph edges
- Each edge linked to source documents with quotes
- Unknowns explicitly stated
- Contradictions surfaced, not hidden

### Interfaces

```bash
mycelium ask "question"              # one-shot CLI
echo "question" | mycelium ask --json  # pipe-friendly
mycelium serve --port 8000           # API server
# POST /ask, GET /graph/subgraph, GET /agents
# WebSocket /ask/stream, /observe/stream
```

### Call Budget

2-4 calls per query (bounded, predictable).

---

## 8. Observation Layer

### What It Captures

| Category | Retention |
|:--|:--|
| Event stream (every bus event) | Indefinite |
| Call ledger (every Claude CLI call) | Indefinite |
| Learn sessions | Indefinite |
| Agent lifecycle | Indefinite |
| Health metrics | 30-day rolling |
| Graph growth | Indefinite |

### Interfaces

1. **Live TUI** (`mycelium observe`) — Textual-based dashboard: mode, budget, live events, graph stats, agent roster, errors
2. **REST API** — `GET /observe/events`, `/sessions`, `/agents`, `/health`, `/graph/growth`. WebSocket `/observe/stream`
3. **CLI Snapshot** — `mycelium status` (quick), `mycelium status --full` (detailed), `mycelium history` (past sessions)

### Design

- Read-only — never modifies state
- Subscribes to `mycelium.>` (NATS wildcard) — sees everything automatically
- New modules observed without changes to observation layer
- Separate `observation.db` — can be wiped without affecting knowledge
- `mycelium observe vacuum --keep-days 90` for cleanup

---

## 9. Data Storage

### brainstem.db (Knowledge Graph)

```sql
-- Entities
CREATE TABLE entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    entity_class TEXT NOT NULL,
    entity_subclass TEXT,
    domain TEXT,
    aliases TEXT,               -- JSON array
    description TEXT,
    properties TEXT,            -- JSON object
    provenance TEXT,            -- JSON array of document IDs
    confidence REAL NOT NULL DEFAULT 0.5,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    last_validated TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    quarantined INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0
);

-- Relationships
CREATE TABLE relationships (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES entities(id),
    target_id TEXT NOT NULL REFERENCES entities(id),
    rel_type TEXT NOT NULL,
    rel_category TEXT NOT NULL,
    rationale TEXT,
    evidence TEXT,              -- JSON array of Evidence
    confidence REAL NOT NULL DEFAULT 0.5,
    strength REAL NOT NULL DEFAULT 0.5,
    bidirectional INTEGER NOT NULL DEFAULT 0,
    temporal_valid_from TEXT,
    temporal_valid_until TEXT,
    is_permanent INTEGER NOT NULL DEFAULT 0,
    contradiction_of TEXT,
    decay_rate REAL NOT NULL DEFAULT 0.05,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    last_validated TEXT,
    quarantined INTEGER NOT NULL DEFAULT 0,
    archived INTEGER NOT NULL DEFAULT 0
);

-- Documents
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    last_ingested TEXT NOT NULL,
    entity_count INTEGER DEFAULT 0,
    edge_count INTEGER DEFAULT 0,
    incomplete INTEGER NOT NULL DEFAULT 0
);

-- Agents
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    domain TEXT NOT NULL,
    description TEXT,
    seed_nodes TEXT,
    status TEXT NOT NULL CHECK(status IN ('candidate', 'active', 'mature', 'retired')),
    queries_answered INTEGER DEFAULT 0,
    avg_confidence REAL DEFAULT 0.0,
    discovered_at TEXT NOT NULL,
    last_active TEXT,
    pinned INTEGER NOT NULL DEFAULT 0
);

-- Agent-Node membership (evolving, updated each cycle)
CREATE TABLE agent_nodes (
    agent_id TEXT NOT NULL REFERENCES agents(id),
    entity_id TEXT NOT NULL REFERENCES entities(id),
    cycle_assigned INTEGER NOT NULL,
    PRIMARY KEY (agent_id, entity_id)
);

-- Concepts (also stored as entities with entity_class='concept' for graph traversal)
CREATE TABLE concepts (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL REFERENCES entities(id),  -- corresponding graph node
    label TEXT NOT NULL,
    description TEXT,
    member_entities TEXT,
    confidence REAL NOT NULL DEFAULT 0.5,
    formed_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);

-- Document chunks (for provenance tracking on large documents)
CREATE TABLE document_chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL REFERENCES documents(id),
    chunk_index INTEGER NOT NULL,
    start_offset INTEGER NOT NULL,
    end_offset INTEGER NOT NULL,
    content_hash TEXT NOT NULL
);

-- Schema version (for migrations)
CREATE TABLE schema_version (
    version INTEGER NOT NULL,
    applied_at TEXT NOT NULL
);

-- Staging (perception pipeline intermediate results)
CREATE TABLE staging_entities (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    layer INTEGER NOT NULL,     -- 1-5
    data TEXT NOT NULL,         -- JSON
    status TEXT NOT NULL,       -- pending, committed, discarded
    created_at TEXT NOT NULL
);

-- Indexes
CREATE INDEX idx_entities_domain ON entities(domain);
CREATE INDEX idx_entities_class ON entities(entity_class);
CREATE INDEX idx_entities_confidence ON entities(confidence);
CREATE INDEX idx_relationships_source ON relationships(source_id);
CREATE INDEX idx_relationships_target ON relationships(target_id);
CREATE INDEX idx_relationships_type ON relationships(rel_type);
CREATE INDEX idx_documents_source ON documents(source);
CREATE INDEX idx_documents_hash ON documents(content_hash);
CREATE INDEX idx_agents_status ON agents(status);
CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_entities_canonical ON entities(canonical_name);
CREATE INDEX idx_agent_nodes_agent ON agent_nodes(agent_id);
CREATE INDEX idx_agent_nodes_entity ON agent_nodes(entity_id);
CREATE INDEX idx_document_chunks_doc ON document_chunks(document_id);
```

### observation.db

```sql
-- Event log
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    event_type TEXT NOT NULL,
    subject TEXT NOT NULL,
    payload TEXT NOT NULL,
    module TEXT
);

-- Learn sessions
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    status TEXT NOT NULL,
    budget INTEGER NOT NULL,
    spent INTEGER NOT NULL DEFAULT 0,
    documents_processed TEXT,
    documents_remaining TEXT,
    entities_created INTEGER DEFAULT 0,
    edges_created INTEGER DEFAULT 0,
    agents_discovered INTEGER DEFAULT 0,
    spillovers INTEGER DEFAULT 0,
    last_checkpoint TEXT
);

-- Call ledger
CREATE TABLE calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT REFERENCES sessions(id),
    call_number INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    task_type TEXT NOT NULL,
    module TEXT NOT NULL,
    input_tokens_est INTEGER,
    output_tokens_est INTEGER,
    duration_ms INTEGER,
    success INTEGER NOT NULL DEFAULT 1
);

-- Health metrics
CREATE TABLE health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    module TEXT NOT NULL,
    metric TEXT NOT NULL,
    value REAL NOT NULL
);

-- Indexes
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_calls_session ON calls(session_id);
CREATE INDEX idx_health_module ON health(module, timestamp);
```

---

## 10. Configuration

### mycelium.toml

```toml
[mycelium]
data_dir = "data"

[nats]
url = "nats://localhost:4222"
stream_prefix = "mycelium"
max_pending = 1024

[connectors.vault]
enabled = true
path = "/Users/kuldeep.luvani/Documents/my_org/Obsidian/Zefr/Zefr"
extensions = [".md"]
ignore_patterns = [".obsidian/*", ".trash/*"]

[connectors.git]
enabled = true
base_path = "/Users/kuldeep.luvani/Documents/zefr_work/Github"
include_repos = []
exclude_repos = ["node_modules", "__pycache__", "delete_me", "delete-me"]
extract_commits = true
extract_readme = true
extract_structure = true
commit_lookback_days = 30
max_repos_per_cycle = 10

[perception]
max_concurrent_pipelines = 3
max_concurrent_cli_calls = 3
batch_size_relationships = 15
batch_size_resolution = 10
chunk_size = 3000
chunk_overlap = 500
quarantine_threshold = 0.4
challenge_skip_anchor_ratio = 0.8
anomaly_entity_limit = 50
anomaly_edge_limit = 100

[brainstem]
db_path = "data/brainstem.db"
embeddings_path = "data/embeddings.faiss"
embedding_model = "local"

[brainstem.decay]
structural = 0.02
causal = 0.05
semantic = 0.10
temporal = 0.15
prune_threshold = 0.1
tombstone_threshold = 0.05
archive_after_cycles = 10

[network]
min_cluster_size = 10
min_coherence = 0.3
max_inter_density = 0.15
stability_cycles = 2
spillover_edge_threshold = 5
min_graph_nodes_for_discovery = 50

[serve]
host = "127.0.0.1"
port = 8000
max_agents_per_query = 3
subgraph_hops = 3

[observe]
db_path = "data/observation.db"
health_retention_days = 30
event_retention_days = -1

[quota]
default_budget = 50
presets = { quick = 20, standard = 50, deep = 100 }
```

---

## 11. Project Structure

```
mycelium/
  pyproject.toml
  nats-server.conf
  mycelium.toml
  Makefile

  src/mycelium/
    __init__.py
    cli.py                       # Click CLI entry points

    bus/
      __init__.py
      events.py                  # All event dataclasses
      publisher.py               # Typed publish
      subscriber.py              # Typed subscribe
      bus.py                     # Bus lifecycle

    orchestrator/
      __init__.py
      orchestrator.py            # Mode manager, learn cycle
      quota.py                   # Call budget tracker
      priority.py                # Priority scorer + queue
      session.py                 # Learn session persistence

    connectors/
      __init__.py
      base.py                    # BaseConnector interface
      vault.py                   # Obsidian vault connector
      git.py                     # Git repo connector
      registry.py                # Connector registration

    perception/
      __init__.py
      engine.py                  # 5-layer pipeline orchestration
      structural.py              # Layer 1: rule-based pre-parse
      extractor.py               # Layer 2: LLM deep extraction
      challenger.py              # Layer 3: adversarial challenge
      consistency.py             # Layer 4: graph consistency
      reconciler.py              # Layer 5: conflict reconciliation
      entity_resolver.py         # Dedup engine
      relationship_builder.py    # Batched relationship extraction
      concept_builder.py         # Higher-order concepts

    brainstem/
      __init__.py
      graph.py                   # NetworkX graph + models
      store.py                   # SQLite persistence
      embeddings.py              # FAISS vector index
      search.py                  # Hybrid search
      cache.py                   # Hot cache
      decay.py                   # Confidence lifecycle

    network/
      __init__.py
      cluster.py                 # Louvain community detection
      agent_manager.py           # Agent lifecycle
      agent.py                   # Agent model
      spillover.py               # Cross-domain transfer
      gap_detector.py            # Missing connection analysis

    serve/
      __init__.py
      intent.py                  # Query intent parsing
      router.py                  # Agent selection
      reasoner.py                # Parallel agent reasoning
      synthesizer.py             # Response synthesis
      feedback.py                # User feedback loop
      api.py                     # FastAPI + WebSocket

    observe/
      __init__.py
      observer.py                # Event subscriber + persistence
      store.py                   # observation.db
      tui.py                     # Textual live dashboard
      api.py                     # REST + WebSocket

    shared/
      __init__.py
      llm.py                     # Claude CLI wrapper
      models.py                  # Core dataclasses
      config.py                  # TOML config loader
      process_guard.py           # Single instance guard (PID file + signal handling)

    migrations/                    # SQLite schema migrations
      __init__.py
      001_initial.py

  data/
    .gitkeep

  tests/
    unit/
    integration/
    fixtures/

  docs/
    design.md
```

---

## 12. Tech Stack

| Layer | Technology | Purpose |
|:--|:--|:--|
| Event Bus | NATS JetStream | Production message broker, free, 10M msg/sec |
| Application | Python 3.11+ (async) | LLM orchestration, graph logic |
| Graph | NetworkX + SQLite | In-memory compute + persistent storage |
| Vectors | FAISS + sentence-transformers | Local embedding generation + similarity search |
| NLP | spaCy (en_core_web_sm) | Layer 1 structural pre-parse |
| TUI | Textual | Live observation dashboard |
| API | FastAPI + uvicorn | Serve mode REST + WebSocket |
| CLI | Click + Rich | Command-line interface |
| LLM | Claude CLI (claude -p) | All reasoning and extraction |
| Config | TOML (tomli) | Settings management |

### External Requirements

- `nats-server` — `brew install nats-server` (free, one-time)
- `spacy model` — `python -m spacy download en_core_web_sm` (one-time)
- Claude CLI — already installed

---

## 13. CLI Commands

```bash
mycelium init                          # Setup: create data dir, init DBs, verify NATS, download spaCy
mycelium learn --calls 50              # Start learn cycle with 50-call budget
mycelium learn --quick                 # Preset: 20 calls
mycelium learn --deep                  # Preset: 100 calls
mycelium serve                         # Start API server on :8000
mycelium ask "question"                # One-shot query
mycelium ask --json "question"         # JSON output
mycelium status                        # Quick summary
mycelium status --full                 # Detailed breakdown
mycelium history                       # Past learn sessions
mycelium observe                       # Live TUI dashboard
mycelium observe vacuum --keep-days 90 # Clean old observation data
mycelium agents list                   # All discovered agents
mycelium agents merge A B              # Force merge
mycelium agents split X --by tag       # Split agent
mycelium agents rename X "New Name"    # Rename
mycelium agents pin "Name"             # Prevent retirement
mycelium agents create --seed "a,b,c"  # Manual agent
mycelium backup                        # Atomic snapshot of all data
mycelium export --format json          # Export graph as JSON
mycelium rebuild-embeddings            # Re-embed all entities (after model change)
```

---

## 14. Cold Start & First-Run

### NATS Lifecycle

NATS runs as a launchd user agent (macOS) or systemd service (Linux), not as a child process of Mycelium. `mycelium init` installs the service. This ensures JetStream durability survives Mycelium crashes.

```bash
mycelium init  # installs nats-server as launchd agent, verifies connectivity
```

If NATS is unresponsive, modules detect via health check (5s ping interval) and publish `ErrorOccurred` locally (stderr + file log fallback). Orchestrator pauses learn cycle until NATS recovers.

### First-Run Behavior

On first `mycelium learn`:
1. NATS verified running (launchd agent)
2. Empty FAISS index — entity resolver uses name/alias only
3. Empty graph — Layer 4 consistency check is no-op
4. No clusters — agent discovery deferred until 50+ nodes
5. Layer 3 challenge skip decision tree:
   - First cycle (no graph): SKIP (no anchors to compare against)
   - Subsequent cycles, Layer 1 found >80% entities: SKIP (already grounded)
   - All other cases: RUN
6. Progressive: first cycle builds foundation, subsequent cycles enrich

---

## 15. Known Risks & Mitigations

| Risk | Impact | Mitigation |
|:--|:--|:--|
| Claude CLI auth failure | Learn cycle stalls | Auth check on startup, retry x2, graceful skip |
| Claude CLI rate limit | Budget underutilized | Exponential backoff, resume from checkpoint |
| NATS crash | All communication stops | Auto-restart, JetStream replay on recovery |
| SQLite corruption | Knowledge lost | WAL mode, regular backups, integrity checks |
| Large repo scan | Budget exhausted on ingestion | max_repos_per_cycle, progressive coverage |
| Hallucinated entities | Graph pollution | 5-layer verification, quarantine, anomaly detection |
| Entity resolver false merges | Knowledge corruption | Conservative thresholds, LLM arbitration, human override |
| Serve API exposed on 0.0.0.0 | Unauthorized network access | Default to 127.0.0.1; optional API key auth for non-localhost |
| Observation DB growth | Disk usage | Retention policies, vacuum command, auto-vacuum option |
| Concurrent Claude CLI calls | Auth/rate limit conflicts | Validate concurrent `claude -p` empirically at init; fallback to serial with async I/O |
| GitHub API rate limits | Git connector PR extraction stalls | Rate limit tracking, defer PR extraction to separate optional pass |
| Unbounded feedback confidence | Edge confidence over/under-correction | Bounded: boost +0.03 per acceptance (cap 0.99), penalty -0.05 per correction (floor 0.1) |

---

## 16. Additional Design Details

### Serve Mode Authentication

Default bind: `127.0.0.1:8000` (localhost only). For non-localhost access, optional API key auth via `[serve] api_key = "..."` in config. No API key = reject non-localhost requests.

### Backup & Export

```bash
mycelium backup                     # Atomic snapshot: brainstem.db + observation.db + embeddings.faiss → data/backups/
mycelium backup --path /external    # Custom backup location
mycelium export --format json       # Export full graph as JSON
mycelium export --format graphml    # Export for external graph tools
```

Backup uses SQLite `.backup()` API for consistency. FAISS index copied atomically. Backups timestamped: `backup-YYYYMMDD-HHMMSS/`.

### Embedding Model

Default: `all-MiniLM-L6-v2` (384 dimensions, ~80MB). Chosen for speed/quality balance on local hardware. FAISS index dimensionality locked at creation — changing models requires full re-embed via `mycelium rebuild-embeddings`. Config documents this lock-in.

### Process Guard

PID file at `data/mycelium.pid`. On startup:
1. Check if PID file exists
2. If exists, check if process is alive (`os.kill(pid, 0)`)
3. If alive, abort with error (only one Mycelium instance per data dir)
4. If stale, remove PID file and proceed
5. Write current PID, register `atexit` handler to clean up

Signal handling: SIGTERM/SIGINT trigger graceful shutdown (same as `QuotaExhausted` drain path).

### SQLite WAL Configuration

Both databases run in WAL mode with explicit checkpoint policy:
- Checkpoint after each learn cycle completes
- Checkpoint when WAL exceeds 50MB
- `PRAGMA wal_autocheckpoint = 1000` (pages) as safety net

### Schema Migrations

`schema_version` table tracks current version. On startup, Mycelium checks version and runs pending migrations sequentially. Migrations are Python files in `src/mycelium/migrations/` named `NNN_description.py`. Each migration is a transaction — if it fails, it rolls back cleanly.
