import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import psycopg2.extensions

import psycopg2

from ezmig.adapters.base import DatabaseAdapter
from ezmig.migration import Migration, MigrationState
from ezmig.utils import split_sql


class PostgresAdapter(DatabaseAdapter):
    def __init__(self, url: str) -> None:
        self.url = url
        self.conn: psycopg2.extensions.connection | None = None
        self.connect()

    def connect(self) -> None:
        self.conn = psycopg2.connect(self.url)
        self.conn.autocommit = False
        self.ensure_schema()

    def _get_conn(self) -> "psycopg2.extensions.connection":
        if self.conn is None:
            self.connect()
        assert self.conn is not None
        return self.conn

    def ensure_schema(self) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ezmig_migrations (
                    version       TEXT PRIMARY KEY,
                    type          TEXT NOT NULL,
                    checksum      TEXT NOT NULL,
                    applied_at    DOUBLE PRECISION NOT NULL,
                    execution_ms  INTEGER
                )
                """
            )
        conn.commit()

    def migrations(self) -> list[Migration]:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT version, type, checksum, execution_ms FROM ezmig_migrations ORDER BY applied_at"
            )
            return [
                Migration(
                    filename=version,
                    path=None,
                    type=type_,
                    duration_ms=execution_ms,
                    stored_checksum=checksum,
                    state=MigrationState.APPLIED,
                )
                for version, type_, checksum, execution_ms in cur.fetchall()
            ]

    def checksums(self) -> set[str]:
        return {m.checksum for m in self.migrations()}

    def record_migration(self, migration: Migration) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ezmig_migrations (version, type, checksum, applied_at, execution_ms)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (version) DO UPDATE SET
                    type         = EXCLUDED.type,
                    checksum     = EXCLUDED.checksum,
                    applied_at   = EXCLUDED.applied_at,
                    execution_ms = EXCLUDED.execution_ms
                """,
                (
                    migration.filename,
                    migration.type,
                    migration.checksum,
                    time.time(),
                    migration.duration_ms,
                ),
            )
        conn.commit()

    def remove_migration(self, migration_hash: str) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM ezmig_migrations WHERE checksum = %s", (migration_hash,))
        conn.commit()

    def execute(self, sql: str) -> None:
        conn = self._get_conn()
        with conn.cursor() as cur:
            for statement in split_sql(sql):
                cur.execute(statement)
        conn.commit()

    def begin(self) -> None:
        # psycopg2 starts transactions automatically; ensure autocommit is off
        conn = self._get_conn()
        conn.autocommit = False

    def commit(self) -> None:
        self._get_conn().commit()

    def rollback(self) -> None:
        self._get_conn().rollback()
