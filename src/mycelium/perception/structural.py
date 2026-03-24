"""Layer 1: Rule-based structural pre-parse. Zero LLM calls."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from mycelium.shared.models import Document


@dataclass
class StructuralEntity:
    name: str
    entity_class: str
    source: str  # "header", "frontmatter", "wikilink", "code", "date", "url"


@dataclass
class StructuralResult:
    entities: list[StructuralEntity] = field(default_factory=list)
    anchors: dict[str, str] = field(default_factory=dict)  # name -> entity_class
    anchor_ratio: float = 0.0  # fraction of total expected entities found structurally


class StructuralParser:
    """Extract ground truth entities from document structure. No LLM calls."""

    # Regex patterns
    _WIKILINK = re.compile(r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]')
    _HEADER = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)
    _DATE = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')
    _URL = re.compile(r'https?://[^\s\)\"]+')
    _CODE_BLOCK = re.compile(r'```(\w+)?.*?```', re.DOTALL)
    _INLINE_CODE = re.compile(r'`([^`]+)`')

    def parse(self, document: Document) -> StructuralResult:
        entities = []
        content = document.content

        # Extract from frontmatter metadata
        for key, value in document.metadata.items():
            if key == "repo" and isinstance(value, str):
                entities.append(StructuralEntity(name=value, entity_class="service", source="frontmatter"))
            elif key == "team" and isinstance(value, str):
                entities.append(StructuralEntity(name=value, entity_class="team", source="frontmatter"))
            elif key == "tags" and isinstance(value, list):
                for tag in value:
                    entities.append(StructuralEntity(name=str(tag), entity_class="tag", source="frontmatter"))
            elif key == "service" and isinstance(value, str):
                # Strip wikilink syntax if present
                clean = value.strip("[]").replace("[[", "").replace("]]", "")
                entities.append(StructuralEntity(name=clean, entity_class="service", source="frontmatter"))

        # Wikilinks
        for match in self._WIKILINK.finditer(content):
            entities.append(StructuralEntity(name=match.group(1).strip(), entity_class="reference", source="wikilink"))

        # Headers
        for match in self._HEADER.finditer(content):
            entities.append(StructuralEntity(name=match.group(1).strip(), entity_class="topic", source="header"))

        # Dates
        for match in self._DATE.finditer(content):
            entities.append(StructuralEntity(name=match.group(1), entity_class="date", source="date"))

        # URLs
        for match in self._URL.finditer(content):
            entities.append(StructuralEntity(name=match.group(0), entity_class="url", source="url"))

        # Inline code (potential service/tech names)
        for match in self._INLINE_CODE.finditer(content):
            name = match.group(1).strip()
            if len(name) > 1 and len(name) < 60:
                entities.append(StructuralEntity(name=name, entity_class="code_ref", source="code"))

        # Build anchors
        anchors = {}
        for e in entities:
            anchors[e.name] = e.entity_class

        # Estimate anchor ratio (heuristic: ~1 entity per 200 chars of content)
        expected = max(1, len(content) // 200)
        anchor_ratio = min(1.0, len(entities) / expected)

        return StructuralResult(entities=entities, anchors=anchors, anchor_ratio=anchor_ratio)
