from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import oracledb as oracledb_types

from ezmig.adapters.base import DatabaseAdapter, SQLExecutionError
from ezmig.migration import Migration, MigrationState
from ezmig.utils import parse_oracle_connection, split_sql

try:
    import oracledb
except ImportError:
    oracledb = None  # type: ignore[assignment,misc]


class OracleAdapter(DatabaseAdapter):
    _PLSQL_PREFIXES = (
        "begin",
        "declare",
        "create or replace procedure",
        "create or replace function",
        "create or replace package",
        "create or replace trigger",
        "create or replace type",
    )

    _SQLPLUS_COMMAND_PREFIXES = (
        "set",
        "spool",
        "prompt",
        "pause",
        "column",
        "col",
        "whenever",
        "accept",
        "define",
        "undefine",
        "connect",
        "conn",
        "host",
        "@",
        "@@",
        "start",
        "exit",
        "quit",
        "show",
    )

    _SQLPLUS_EXACT_COMMANDS = (
        "clear",
    )

    def __init__(self, url: str) -> None:
        self.url = url
        self.conn: oracledb_types.Connection | None = None

    def connect(self) -> None:
        if oracledb is None:
            raise RuntimeError(
                "oracledb is not installed. Install with: pip install 'ezmig[oracle]'"
            )
        if not self.conn:
            dsn, user, password = parse_oracle_connection(self.url)
            connect_kwargs = {"dsn": dsn}
            if user is not None:
                connect_kwargs["user"] = user
            if password is not None:
                connect_kwargs["password"] = password

            try:
                self.conn = oracledb.connect(**connect_kwargs)
            except oracledb.DatabaseError as exc:
                if "DPY-4001" in str(exc):
                    raise RuntimeError(
                        "Oracle credentials are missing. Use URL format: "
                        "oracle://user:password@host:port/?service_name=SERVICE"
                    ) from exc
                raise

    def _get_conn(self) -> "oracledb_types.Connection":
        if self.conn is None:
            self.connect()
        assert self.conn is not None
        return self.conn

    def ensure_schema(self) -> None:
        cur = self._get_conn().cursor()

        try:
            cur.execute(
                """
                CREATE TABLE ezmig_migrations (
                    version       VARCHAR2(255) PRIMARY KEY,
                    type          VARCHAR2(10) NOT NULL,
                    checksum      VARCHAR2(64) NOT NULL,
                    applied_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    execution_ms  NUMBER
                )
                """
            )
        except oracledb.DatabaseError as e:
            # ORA-00955 = table already exists
            if "ORA-00955" not in str(e):
                raise

    def migrations(self) -> list[Migration]:
        cur = self._get_conn().cursor()

        cur.execute(
            """
            SELECT version, type, checksum, execution_ms
            FROM ezmig_migrations
            ORDER BY applied_at
            """
        )

        return [
            Migration(
                filename=row[0],
                path=None,
                type=row[1],
                stored_checksum=row[2],
                duration_ms=row[3],
                state=MigrationState.APPLIED,
            )
            for row in cur.fetchall()
        ]

    def checksums(self) -> set[str]:
        return {m.checksum for m in self.migrations()}

    def record_migration(self, migration: Migration) -> None:
        assert self.conn

        cur = self.conn.cursor()
        cur.execute(
            """
            MERGE INTO ezmig_migrations target
            USING (
                SELECT :1 AS version,
                       :2 AS type,
                       :3 AS checksum,
                       :4 AS execution_ms
                FROM dual
            ) source
            ON (target.version = source.version)
            WHEN MATCHED THEN
                UPDATE SET
                    target.type = source.type,
                    target.checksum = source.checksum,
                    target.applied_at = CURRENT_TIMESTAMP,
                    target.execution_ms = source.execution_ms
            WHEN NOT MATCHED THEN
                INSERT (version, type, checksum, applied_at, execution_ms)
                VALUES (
                    source.version,
                    source.type,
                    source.checksum,
                    CURRENT_TIMESTAMP,
                    source.execution_ms
                )
            """,
            (
                migration.filename,
                migration.type,
                migration.checksum,
                migration.duration_ms,
            ),
        )
        self.conn.commit()

    def remove_migration(self, migration_hash: str) -> None:
        assert self.conn

        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM ezmig_migrations WHERE checksum = :1",
            (migration_hash,),
        )
        self.conn.commit()

    def execute(self, sql: str) -> None:
        assert self.conn
        cur = self.conn.cursor()

        cleaned_sql = self._strip_sqlplus_commands(sql)
        statements = [
            normalized
            for statement in split_sql(cleaned_sql)
            if (normalized := self._normalize_statement(statement))
        ]

        for index, statement in enumerate(statements, start=1):
            try:
                cur.execute(statement)
            except Exception as error:
                raise SQLExecutionError(
                    message="Oracle statement execution failed",
                    statement=statement,
                    statement_index=index,
                    total_statements=len(statements),
                    original_error=error,
                ) from error

    @staticmethod
    def _strip_sqlplus_commands(sql: str) -> str:
        cleaned_lines: list[str] = []

        for line in sql.splitlines():
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append(line)
                continue

            lowered = stripped.lower()

            if lowered.startswith("rem "):
                continue

            if lowered in OracleAdapter._SQLPLUS_EXACT_COMMANDS:
                continue

            if OracleAdapter._starts_with_sqlplus_command(lowered):
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    @staticmethod
    def _starts_with_sqlplus_command(lowered_line: str) -> bool:
        for prefix in OracleAdapter._SQLPLUS_COMMAND_PREFIXES:
            if lowered_line == prefix or lowered_line.startswith(f"{prefix} "):
                return True
        return False

    @staticmethod
    def _normalize_statement(statement: str) -> str:
        normalized = statement.strip()
        if not normalized:
            return ""

        if OracleAdapter._is_comment_only_statement(normalized):
            return ""

        lowered = normalized.lower()
        is_plsql = OracleAdapter._is_plsql_statement(lowered)

        if normalized.endswith(";") and not is_plsql:
            return normalized[:-1].rstrip()

        return normalized

    @staticmethod
    def _is_comment_only_statement(statement: str) -> bool:
        in_block_comment = False

        for line in statement.splitlines():
            remaining = line.strip()

            while remaining:
                if in_block_comment:
                    end_idx = remaining.find("*/")
                    if end_idx == -1:
                        remaining = ""
                        break
                    remaining = remaining[end_idx + 2 :].lstrip()
                    in_block_comment = False
                    continue

                if not remaining.strip(";").strip():
                    remaining = ""
                    break

                lowered = remaining.lower()
                if remaining.startswith("--") or lowered.startswith("rem "):
                    remaining = ""
                    break

                if remaining.startswith("/*"):
                    end_idx = remaining.find("*/", 2)
                    if end_idx == -1:
                        in_block_comment = True
                        remaining = ""
                        break
                    remaining = remaining[end_idx + 2 :].lstrip()
                    continue

                return False

        return True

    @staticmethod
    def _is_plsql_statement(lowered_statement: str) -> bool:
        return lowered_statement.startswith(OracleAdapter._PLSQL_PREFIXES)

    def begin(self) -> None:
        # Oracle auto-commit behavior makes this mostly noop
        pass

    def commit(self) -> None:
        if self.conn:
            self.conn.commit()

    def rollback(self) -> None:
        if self.conn:
            self.conn.rollback()
