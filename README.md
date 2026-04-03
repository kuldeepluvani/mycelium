# Mycelium

A self-enriching, local-first knowledge engine that ingests Obsidian vaults and Git repos into a live knowledge graph, auto-discovers specialist AI agents from data clusters, and answers questions through a hierarchical two-tier cortex.

## Architecture

```
Sources (Vault, Git)
    │
    ▼
5-Layer Perception Engine
  ├─ Structural pre-parse (frontmatter, wikilinks, headers)
  ├─ LLM deep extraction (entities, relationships, claims)
  ├─ Adversarial challenge (verify/reject)
  ├─ Graph consistency check
  └─ Reconciliation (final verdicts + confidence)
    │
    ▼
Knowledge Graph (NetworkX + SQLite + FAISS)
  ├─ Entities with confidence, decay, provenance
  ├─ Relationships with rationale + evidence
  └─ Deduplication (exact → alias → embedding similarity)
    │
    ▼
Agent Cortex
  ├─ L1 Specialists (auto-discovered from Louvain clusters)
  └─ L2 Meta-Agents (supervise L1s, route queries)
```

## Quick Start

```bash
# Install
pip install -e .

# Initialize (creates mycelium.toml + data/)
mycelium init

# Learn from your vault
mycelium learn              # standard (50 calls)
mycelium learn --quick      # quick (20 calls)
mycelium learn --deep       # deep (100 calls)
mycelium learn --force      # re-process all files

# Ask questions
mycelium ask "What services depend on Redis?"
mycelium ask --flat "..."   # bypass cortex, use flat agent routing

# Start web dashboard
mycelium serve              # http://localhost:8000

# Status & agents
mycelium status
mycelium status --full
mycelium agents list
mycelium agents rename <id> "New Name"
mycelium agents pin <id>

# History & observability
mycelium history
mycelium observe            # TUI live event dashboard
mycelium backup [path]
```

## Configuration

All settings in `mycelium.toml`:

| Section | Controls |
|:---|:---|
| `connectors.vault` | Obsidian vault path, file extensions, ignore patterns |
| `connectors.git` | Git repo base path, include/exclude repos, commit lookback |
| `perception` | Chunk size, batch sizes, challenge thresholds, concurrency |
| `brainstem.decay` | Confidence decay rates by relationship category |
| `network` | Cluster size, coherence threshold, spillover settings |
| `serve` | Host, port, max agents per query, subgraph hops |
| `quota` | Budget presets (quick/standard/deep) |

## Web Dashboard

Five tabs at `http://localhost:8000`:

- **Graph Explorer** — D3 force-directed graph with entity/relationship inspection
- **Agent Hierarchy** — L1/L2 agent tree with delegation stats
- **Ask** — Query interface with live cortex routing visualization
- **Learn** — Trigger learning with budget controls and live progress
- **Observe** — Streaming event feed with health monitoring

## API

```
GET  /api/status              Graph stats, agent counts, last learn session
GET  /api/graph/nodes         All entities with confidence
GET  /api/graph/edges         All relationships with rationale
GET  /api/graph/entity/:id    Entity detail + neighbors
GET  /api/graph/diff          Changes since last learn session
GET  /api/agents              L1 agents
GET  /api/agents/hierarchy    L2 meta-agents with children
GET  /api/agents/spillover    Cross-domain analysis results
POST /api/ask                 Query with cortex routing
POST /api/learn/start         Trigger learn cycle
POST /api/feedback/accept     User accepted answer
POST /api/feedback/correct    User corrected answer
WS   /ws/events               Live event stream
```

## Stack

| Layer | Technology |
|:---|:---|
| Graph compute | NetworkX |
| Persistence | SQLite (WAL mode) |
| Embeddings | FAISS + all-MiniLM-L6-v2 |
| Message bus | NATS JetStream |
| LLM | Claude (via CLI) |
| API | FastAPI + WebSocket |
| Frontend | React 18 + D3.js + Tailwind |
| TUI | Textual |
| CLI | Click |

## Requirements

- Python 3.11+
- Claude Code CLI (for LLM calls)
- NATS server (for event bus)
