"""Git repo connector -- discovers repos and extracts content."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import git

from mycelium.connectors.base import BaseConnector
from mycelium.shared.models import ChangeSet, Document


class GitConnector(BaseConnector):
    def __init__(
        self,
        base_path: str,
        include_repos: list[str] | None = None,
        exclude_repos: list[str] | None = None,
        max_repos_per_cycle: int = 10,
        commit_lookback_days: int = 7,
        extract_commits: bool = True,
        extract_readme: bool = True,
        extract_structure: bool = False,
    ) -> None:
        self.base_path = Path(base_path)
        self.include_repos = include_repos or []
        self.exclude_repos = exclude_repos or []
        self.max_repos_per_cycle = max_repos_per_cycle
        self.commit_lookback_days = commit_lookback_days
        self.extract_commits = extract_commits
        self.extract_readme = extract_readme
        self.extract_structure = extract_structure

    def source_type(self) -> str:
        return "git"

    def _find_repos(self) -> list[Path]:
        """Find directories containing .git/ under base_path."""
        repos: list[Path] = []
        if not self.base_path.is_dir():
            return repos
        for child in self.base_path.iterdir():
            if not child.is_dir():
                continue
            if (child / ".git").exists():
                name = child.name
                if self.include_repos and name not in self.include_repos:
                    continue
                if name in self.exclude_repos:
                    continue
                repos.append(child)
        # Sort by most recently modified (newest first)
        repos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return repos[: self.max_repos_per_cycle]

    async def discover_changes(self, since: datetime | None = None) -> list[ChangeSet]:
        if since is None:
            since = datetime.now(timezone.utc) - timedelta(days=self.commit_lookback_days)
        changes: list[ChangeSet] = []
        for repo_path in self._find_repos():
            try:
                repo = git.Repo(repo_path)
            except git.InvalidGitRepositoryError:
                continue
            # Check for commits since the given date
            try:
                commits = list(repo.iter_commits(since=since.isoformat()))
            except (git.GitCommandError, ValueError):
                commits = []
            if commits:
                latest_ts = max(
                    datetime.fromtimestamp(c.committed_date, tz=timezone.utc) for c in commits
                )
                changes.append(
                    ChangeSet(
                        source="git",
                        path=str(repo_path),
                        change_type="modified",
                        diff_summary=f"{len(commits)} commit(s) since {since.date()}",
                        timestamp=latest_ts,
                    )
                )
        return changes

    async def fetch_content(self, path: str) -> Document | None:
        repo_path = Path(path)
        if not repo_path.is_dir():
            return None

        parts: list[str] = []

        # Extract README
        if self.extract_readme:
            readme = repo_path / "README.md"
            if readme.exists():
                parts.append(readme.read_text(encoding="utf-8"))

        # Extract recent commits
        if self.extract_commits:
            try:
                repo = git.Repo(repo_path)
                since_dt = datetime.now(timezone.utc) - timedelta(days=self.commit_lookback_days)
                commits = list(repo.iter_commits(since=since_dt.isoformat(), max_count=20))
                if commits:
                    commit_lines = [f"## Recent Commits ({len(commits)})"]
                    for c in commits[:20]:
                        commit_lines.append(f"- {c.hexsha[:8]} {c.summary}")
                    parts.append("\n".join(commit_lines))
            except (git.InvalidGitRepositoryError, git.GitCommandError):
                pass

        content = "\n\n".join(parts) if parts else ""
        if not content:
            return None

        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        return Document(
            id=repo_path.name,
            source="git",
            path=str(repo_path),
            content=content,
            content_hash=content_hash,
        )
