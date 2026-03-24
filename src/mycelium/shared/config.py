"""TOML config loader with Pydantic validation for Mycelium."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


# ── Sub-configs ──────────────────────────────────────────────────────────────


class NatsConfig(BaseModel):
    url: str = "nats://localhost:4222"
    stream_prefix: str = "mycelium"
    max_pending: int = 1024


class VaultConnectorConfig(BaseModel):
    enabled: bool = True
    path: str = ""
    extensions: list[str] = Field(default_factory=lambda: [".md"])
    ignore_patterns: list[str] = Field(
        default_factory=lambda: [".obsidian/*", ".trash/*"]
    )


class GitConnectorConfig(BaseModel):
    enabled: bool = True
    base_path: str = ""
    include_repos: list[str] = Field(default_factory=list)
    exclude_repos: list[str] = Field(default_factory=list)
    extract_commits: bool = True
    extract_readme: bool = True
    extract_structure: bool = True
    commit_lookback_days: int = 30
    max_repos_per_cycle: int = 10


class ConnectorsConfig(BaseModel):
    vault: VaultConnectorConfig = Field(default_factory=VaultConnectorConfig)
    git: GitConnectorConfig = Field(default_factory=GitConnectorConfig)


class PerceptionConfig(BaseModel):
    max_concurrent_pipelines: int = 3
    max_concurrent_cli_calls: int = 3
    batch_size_relationships: int = 15
    batch_size_resolution: int = 10
    chunk_size: int = 3000
    chunk_overlap: int = 500
    quarantine_threshold: float = 0.4
    challenge_skip_anchor_ratio: float = 0.8
    anomaly_entity_limit: int = 50
    anomaly_edge_limit: int = 100


class DecayConfig(BaseModel):
    structural: float = 0.02
    causal: float = 0.05
    semantic: float = 0.10
    temporal: float = 0.15
    prune_threshold: float = 0.1
    tombstone_threshold: float = 0.05
    archive_after_cycles: int = 10


class BrainstemConfig(BaseModel):
    db_path: str = "data/brainstem.db"
    embeddings_path: str = "data/embeddings.faiss"
    embedding_model: str = "local"
    decay: DecayConfig = Field(default_factory=DecayConfig)


class NetworkConfig(BaseModel):
    min_cluster_size: int = 10
    min_coherence: float = 0.3
    max_inter_density: float = 0.15
    stability_cycles: int = 2
    spillover_edge_threshold: int = 5
    min_graph_nodes_for_discovery: int = 50


class ServeConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    max_agents_per_query: int = 3
    subgraph_hops: int = 3
    api_key: Optional[str] = None


class ObserveConfig(BaseModel):
    db_path: str = "data/observation.db"
    health_retention_days: int = 30
    event_retention_days: int = -1
    auto_vacuum_threshold_mb: int = 500


class QuotaConfig(BaseModel):
    default_budget: int = 50
    presets: dict[str, int] = Field(
        default_factory=lambda: {"quick": 20, "standard": 50, "deep": 100}
    )


# ── Top-level config ────────────────────────────────────────────────────────


class MyceliumConfig(BaseModel):
    data_dir: Path = Path("data")
    nats: NatsConfig = Field(default_factory=NatsConfig)
    connectors: ConnectorsConfig = Field(default_factory=ConnectorsConfig)
    perception: PerceptionConfig = Field(default_factory=PerceptionConfig)
    brainstem: BrainstemConfig = Field(default_factory=BrainstemConfig)
    network: NetworkConfig = Field(default_factory=NetworkConfig)
    serve: ServeConfig = Field(default_factory=ServeConfig)
    observe: ObserveConfig = Field(default_factory=ObserveConfig)
    quota: QuotaConfig = Field(default_factory=QuotaConfig)


# ── Loader ───────────────────────────────────────────────────────────────────


def load_config(config_path: Path) -> MyceliumConfig:
    """Load and validate a Mycelium TOML configuration file.

    Reads the TOML file at *config_path*, extracts the ``[mycelium]`` table,
    and returns a fully-validated :class:`MyceliumConfig`.  If ``data_dir`` is
    relative it is resolved against the directory containing the config file.
    """
    with open(config_path, "rb") as fh:
        raw = tomllib.load(fh)

    # Merge [mycelium] section with top-level sections (nats, connectors, etc.)
    merged: dict = {}
    mycelium_raw = raw.get("mycelium", {})
    merged.update(mycelium_raw)

    for key in ("nats", "connectors", "perception", "brainstem", "network", "serve", "observe", "quota"):
        if key in raw:
            merged[key] = raw[key]

    config = MyceliumConfig(**merged)

    # Resolve data_dir relative to the config file's parent directory.
    if not config.data_dir.is_absolute():
        config.data_dir = (config_path.parent / config.data_dir).resolve()

    return config
