"""Obsidian vault connector -- discovers and parses markdown files."""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path

import yaml

from mycelium.connectors.base import BaseConnector
from mycelium.shared.models import ChangeSet, Document

_WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class VaultConnector(BaseConnector):
    def __init__(
        self,
        vault_path: str,
        extensions: list[str] | None = None,
        ignore_patterns: list[str] | None = None,
    ) -> None:
        self.vault_path = Path(vault_path)
        self.extensions = extensions or [".md"]
        self.ignore_patterns = ignore_patterns or []

    def source_type(self) -> str:
        return "vault"

    def _should_ignore(self, rel_path: str) -> bool:
        for pattern in self.ignore_patterns:
            if fnmatch(rel_path, pattern):
                return True
        return False

    async def discover_changes(self, since: datetime | None = None, **kwargs) -> list[ChangeSet]:
        known_hashes = kwargs.get("known_hashes")
        changes: list[ChangeSet] = []
        for root, _dirs, files in os.walk(self.vault_path):
            for fname in files:
                full = Path(root) / fname
                if full.suffix not in self.extensions:
                    continue
                rel = str(full.relative_to(self.vault_path))
                if self._should_ignore(rel):
                    continue
                mtime = datetime.fromtimestamp(full.stat().st_mtime, tz=timezone.utc)
                if since is not None and mtime <= since:
                    continue

                # Content-hash check: skip if content hasn't changed
                if known_hashes is not None:
                    content_hash = hashlib.sha256(full.read_bytes()).hexdigest()
                    stored_hash = known_hashes.get_document_hash(str(full))
                    if stored_hash == content_hash:
                        continue

                changes.append(
                    ChangeSet(
                        source="vault",
                        path=str(full),
                        change_type="modified",
                        timestamp=mtime,
                    )
                )
        return changes

    async def fetch_content(self, path: str) -> Document | None:
        p = Path(path)
        if not p.exists():
            return None
        raw = p.read_text(encoding="utf-8")
        content_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()

        # Parse YAML frontmatter
        metadata: dict = {}
        fm_match = _FRONTMATTER_RE.match(raw)
        if fm_match:
            try:
                metadata = yaml.safe_load(fm_match.group(1)) or {}
            except yaml.YAMLError:
                metadata = {}

        # Extract wikilinks
        wikilinks = _WIKILINK_RE.findall(raw)

        doc_id = str(p.relative_to(self.vault_path)) if p.is_relative_to(self.vault_path) else p.name

        return Document(
            id=doc_id,
            source="vault",
            path=str(p),
            content=raw,
            content_hash=content_hash,
            metadata=metadata,
            wikilinks=wikilinks,
        )
