"""Tests for GitConnector."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from mycelium.connectors.git import GitConnector


def _init_repo(path: Path, readme_content: str | None = None) -> None:
    """Initialise a bare-minimum git repo with an optional README commit."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", str(path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@test.com"],
        capture_output=True,
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test"],
        capture_output=True,
        check=True,
    )
    if readme_content is not None:
        (path / "README.md").write_text(readme_content)
        subprocess.run(["git", "-C", str(path), "add", "."], capture_output=True, check=True)
        subprocess.run(
            ["git", "-C", str(path), "commit", "-m", "init"],
            capture_output=True,
            check=True,
        )


@pytest.fixture
def repos_dir(tmp_path: Path) -> Path:
    _init_repo(tmp_path / "repo-alpha", readme_content="# Alpha\n")
    _init_repo(tmp_path / "repo-beta", readme_content="# Beta\n")
    return tmp_path


async def test_discover_repos(repos_dir: Path):
    gc = GitConnector(base_path=str(repos_dir))
    changes = await gc.discover_changes()
    names = [Path(c.path).name for c in changes]
    assert "repo-alpha" in names
    assert "repo-beta" in names


async def test_exclude_repos(repos_dir: Path):
    gc = GitConnector(base_path=str(repos_dir), exclude_repos=["repo-beta"])
    changes = await gc.discover_changes()
    names = [Path(c.path).name for c in changes]
    assert "repo-alpha" in names
    assert "repo-beta" not in names


async def test_max_repos_per_cycle(repos_dir: Path):
    gc = GitConnector(base_path=str(repos_dir), max_repos_per_cycle=1)
    changes = await gc.discover_changes()
    assert len(changes) <= 1


async def test_fetch_readme(repos_dir: Path):
    gc = GitConnector(base_path=str(repos_dir), extract_commits=False)
    doc = await gc.fetch_content(str(repos_dir / "repo-alpha"))
    assert doc is not None
    assert "# Alpha" in doc.content
    assert doc.source == "git"
    assert doc.id == "repo-alpha"
