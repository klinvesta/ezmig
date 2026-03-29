import sqlite3
import time

from ezmig.adapters.base import DatabaseAdapter
from ezmig.migration import Migration, MigrationState


class SQLiteAdapter(DatabaseAdapter):
    def __init__(self, url: str = ":memory:"):
        self.url = url or ":memory:"
        self.conn: sqlite3.Connection | None = None
        self.connect()

    def connect(self) -> None:
        self.conn = sqlite3.connect(self.url)
        self.ensure_schema()

    def ensure_schema(self) -> None:
        assert self.conn
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ezmig_migrations (
                version TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at REAL NOT NULL,
                execution_ms INTEGER
            )
            """
        )
        self.conn.commit()

    def migrations(self) -> list[Migration]:
        """Return applied migrations as Migration instances (no file needed)."""
        assert self.conn
        cur = self.conn.execute(
            "SELECT version, type, checksum, execution_ms FROM ezmig_migrations ORDER BY applied_at"
        )
        applied = [
            Migration(
                filename=version,
                path=None,
                type=type,
                duration_ms=execution_ms,
                stored_checksum=checksum,
                state=MigrationState.APPLIED,
            )
            for version, type, checksum, execution_ms in cur.fetchall()
        ]
        return applied

    def checksums(self) -> set[str]:
        return {m.checksum for m in self.migrations()}

    def record_migration(self, migration: Migration) -> None:
        assert self.conn
        self.conn.execute(
            """
            INSERT INTO ezmig_migrations (version, type, checksum, applied_at, execution_ms)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(version) DO UPDATE SET
                type = excluded.type,
                checksum = excluded.checksum,
                applied_at = excluded.applied_at,
                execution_ms = excluded.execution_ms
            """,
            (
                migration.filename,
                migration.type,
                migration.checksum,
                time.time(),
                migration.duration_ms,
            ),
        )
        self.conn.commit()

    def remove_migration(self, migration_hash: str) -> None:
        assert self.conn
        self.conn.execute("DELETE FROM ezmig_migrations WHERE checksum = ?", (migration_hash,))
        self.conn.commit()

    def execute(self, sql: str) -> None:
        assert self.conn
        self.conn.executescript(sql)
        self.conn.commit()

    def begin(self) -> None:
        assert self.conn
        self.conn.execute("BEGIN")

    def commit(self) -> None:
        assert self.conn
        self.conn.commit()

    def rollback(self) -> None:
        assert self.conn
        self.conn.rollback()
