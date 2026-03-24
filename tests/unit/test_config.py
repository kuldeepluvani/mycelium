"""Tests for the TOML config loader."""

from pathlib import Path

from mycelium.shared.config import load_config


def test_load_default_config(tmp_path: Path) -> None:
    """Minimal TOML loads and populates expected defaults."""
    cfg_file = tmp_path / "mycelium.toml"
    cfg_file.write_text(
        "[mycelium]\n"
        'data_dir = "data"\n'
    )

    cfg = load_config(cfg_file)

    assert cfg.nats.url == "nats://localhost:4222"
    assert cfg.quota.default_budget == 50


def test_data_dir_resolved_relative_to_config(tmp_path: Path) -> None:
    """Relative data_dir is resolved against the config file's directory."""
    cfg_file = tmp_path / "mycelium.toml"
    cfg_file.write_text(
        "[mycelium]\n"
        'data_dir = "data"\n'
    )

    cfg = load_config(cfg_file)

    assert cfg.data_dir == (tmp_path / "data").resolve()


def test_data_dir_absolute_path(tmp_path: Path) -> None:
    """Absolute data_dir is preserved as-is."""
    abs_dir = tmp_path / "absolute_data"
    cfg_file = tmp_path / "mycelium.toml"
    cfg_file.write_text(
        "[mycelium]\n"
        f'data_dir = "{abs_dir}"\n'
    )

    cfg = load_config(cfg_file)

    assert cfg.data_dir == abs_dir


def test_missing_config_uses_defaults(tmp_path: Path) -> None:
    """An empty [mycelium] table falls back to all defaults."""
    cfg_file = tmp_path / "mycelium.toml"
    cfg_file.write_text("[mycelium]\n")

    cfg = load_config(cfg_file)

    # Spot-check various defaults across sub-configs.
    assert cfg.nats.url == "nats://localhost:4222"
    assert cfg.nats.stream_prefix == "mycelium"
    assert cfg.nats.max_pending == 1024
    assert cfg.connectors.vault.enabled is True
    assert cfg.connectors.git.commit_lookback_days == 30
    assert cfg.perception.chunk_size == 3000
    assert cfg.brainstem.embedding_model == "local"
    assert cfg.brainstem.decay.structural == 0.02
    assert cfg.network.min_cluster_size == 10
    assert cfg.serve.host == "127.0.0.1"
    assert cfg.serve.api_key is None
    assert cfg.observe.health_retention_days == 30
    assert cfg.quota.presets == {"quick": 20, "standard": 50, "deep": 100}
