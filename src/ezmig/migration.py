import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .checksum import compute_checksum

_APPLY_TXT = "-- ezmig:apply"
_ROLLBACK_TXT = "-- ezmig:rollback"

_MARKERS = (_APPLY_TXT, _ROLLBACK_TXT)


def _parse_sections(text: str) -> dict[str, str]:
    """Extract named sections from a migration file.

    Works regardless of the order -- ezmig:apply / -- ezmig:rollback appear.
    Each section's content runs from its marker to the start of the next
    marker (or EOF), so arbitrary ordering is handled without extra tags.
    """
    found = sorted(
        ((text.find(m), m) for m in _MARKERS if m in text),
        key=lambda t: t[0],
    )
    sections: dict[str, str] = {}
    for i, (start, marker) in enumerate(found):
        content_start = start + len(marker)
        content_end = found[i + 1][0] if i + 1 < len(found) else len(text)
        sections[marker] = text[content_start:content_end].strip()
    return sections


class MigrationState(enum.StrEnum):
    APPLIED = "applied"
    PENDING = "pending"
    UNCHANGED = "unchanged"
    CHANGED = "changed"
    UNKNOWN = "unknown"


@dataclass
class Migration:
    filename: str
    path: Path | None
    type: Literal["versioned", "repeatable"]
    duration_ms: int | None = None
    state: MigrationState = field(default=MigrationState.UNKNOWN)
    stored_checksum: str | None = None  # checksum from DB if path not available

    @property
    def checksum(self) -> str:
        if self.stored_checksum is not None:
            return self.stored_checksum
        assert self.path is not None, "Cannot compute checksum without path"
        return compute_checksum(self.path.read_bytes())

    @property
    def down_sql(self) -> str:
        assert self.path, "Cannot read down SQL without path"
        text = self.path.read_text()
        return _parse_sections(text).get(_ROLLBACK_TXT, "")

    @property
    def apply_sql(self) -> str:
        """Return the SQL to execute when applying this migration.

        - Versioned: only the -- ezmig:apply section
        - Repeatable: the whole file
        """
        assert self.path, "Cannot read apply SQL without path"
        text = self.path.read_text()
        if self.type == "repeatable":
            return text
        # fallback: return the whole text if no ezmig:apply marker
        return _parse_sections(text).get(_APPLY_TXT, text.strip())
