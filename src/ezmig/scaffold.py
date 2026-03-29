import re
from datetime import datetime
from pathlib import Path

VERSIONED_TEMPLATE = """-- ezmig:apply

-- write forward migration SQL here

-- ezmig:rollback

-- write rollback SQL here
"""

REPEATABLE_TEMPLATE = """-- write repeatable migration SQL here
"""


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    if not slug:
        raise ValueError("Migration name must contain letters or numbers")
    return slug


def versioned_filename(name: str, now: datetime | None = None) -> str:
    current = now or datetime.now()
    timestamp = current.strftime("%Y%m%d%H%M%S")
    return f"{timestamp}_{slugify(name)}.sql"


def repeatable_filename(name: str) -> str:
    return f"{slugify(name)}.sql"


def create_versioned_migration(
    path: Path,
    name: str,
    now: datetime | None = None,
) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    filename = versioned_filename(name=name, now=now)
    target = path / filename
    if target.exists():
        raise FileExistsError(f"Migration already exists: {target}")
    target.write_text(VERSIONED_TEMPLATE, encoding="utf-8")
    return target


def create_repeatable_migration(path: Path, name: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    filename = repeatable_filename(name=name)
    target = path / filename
    if target.exists():
        raise FileExistsError(f"Migration already exists: {target}")
    target.write_text(REPEATABLE_TEMPLATE, encoding="utf-8")
    return target
