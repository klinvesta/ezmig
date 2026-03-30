import logging
import time
from fnmatch import fnmatch
from pathlib import Path

from .adapters.base import DatabaseAdapter, SQLExecutionError
from .migration import Migration, MigrationState

logger = logging.getLogger("ezmig.runner")


def _truncate_sql(statement: str, max_chars: int = 1200) -> str:
    compact = statement.strip()
    if len(compact) <= max_chars:
        return compact
    return f"{compact[:max_chars].rstrip()}\n... [truncated]"


class MigrationRunner:
    def __init__(
        self,
        versioned_path: Path | list[Path],
        repeatable_path: Path | list[Path],
        adapter: DatabaseAdapter | None = None,
    ) -> None:

        self.adapter = adapter
        self.versioned_paths = self._normalize_paths(versioned_path)
        self.repeatable_paths = self._normalize_paths(repeatable_path)

    @staticmethod
    def _normalize_paths(paths: Path | list[Path]) -> list[Path]:
        if isinstance(paths, Path):
            return [paths]
        if isinstance(paths, list) and paths:
            return paths
        raise ValueError("Migration directories must include at least one path")

    def _load_versioned(self) -> list[Migration]:
        files: list[Path] = []
        for directory in self.versioned_paths:
            files.extend(directory.glob("*.sql"))

        return [
            Migration(filename=file.name, path=file, type="versioned")
            for file in sorted(files, key=lambda item: (item.name, str(item)))
        ]

    def _load_repeatable(self) -> list[Migration]:
        files: list[Path] = []
        for directory in self.repeatable_paths:
            files.extend(directory.glob("*.sql"))

        return [
            Migration(filename=file.name, path=file, type="repeatable")
            for file in sorted(files, key=lambda item: (item.name, str(item)))
        ]

    def _load_all(self) -> list[Migration]:
        return self._load_versioned() + self._load_repeatable()

    def plan(self) -> list[Migration]:
        """
        Return only migrations that would be applied.
        """
        migrations = self.status()

        return [
            m for m in migrations if m.state in (MigrationState.PENDING, MigrationState.CHANGED)
        ]

    def apply(self, force: bool = False, allow_replay: bool = False):
        """
        Apply all pending versioned migrations first, then repeatable migrations.
        Ensures each migration is applied exactly once using its hash.
        """
        if not isinstance(self.adapter, DatabaseAdapter):
            raise RuntimeError("No valid DatabaseAdapter provided")

        if force:
            self.replay(include_all=True, allow_replay=allow_replay)
            return

        for migration in self.plan():
            self._apply_single(migration)

    def replay(
        self,
        *,
        versioned_patterns: list[str] | None = None,
        repeatable_patterns: list[str] | None = None,
        include_all: bool = False,
        allow_replay: bool = False,
    ) -> None:
        if not isinstance(self.adapter, DatabaseAdapter):
            raise RuntimeError("No valid DatabaseAdapter provided")

        if not allow_replay:
            raise RuntimeError(
                "Replay is disabled. Use --allow-replay or enable allow_replay on target"
            )

        adapter: DatabaseAdapter = self.adapter
        adapter.ensure_schema()
        applied_by_name = {migration.filename: migration for migration in adapter.migrations()}

        selected_versioned, selected_repeatable = self._select_replay_migrations(
            versioned_patterns=versioned_patterns,
            repeatable_patterns=repeatable_patterns,
            include_all=include_all,
        )

        for migration in selected_versioned:
            if migration.filename in applied_by_name:
                self._replay_applied_versioned(migration)
            else:
                self._apply_single(migration)

        for migration in selected_repeatable:
            self._apply_single(migration)

    def _select_replay_migrations(
        self,
        *,
        versioned_patterns: list[str] | None,
        repeatable_patterns: list[str] | None,
        include_all: bool,
    ) -> tuple[list[Migration], list[Migration]]:
        has_versioned = bool(versioned_patterns)
        has_repeatable = bool(repeatable_patterns)
        if not include_all and not has_versioned and not has_repeatable:
            raise RuntimeError("Replay selection is empty. Use --migration, --repeatable, or --all")

        versioned = self._load_versioned()
        repeatable = self._load_repeatable()

        if include_all:
            selected_versioned = versioned
            selected_repeatable = repeatable
        else:
            selected_versioned = self._select_by_patterns(versioned, versioned_patterns or [])
            selected_repeatable = self._select_by_patterns(repeatable, repeatable_patterns or [])

        if not selected_versioned and not selected_repeatable:
            raise RuntimeError("No migrations matched replay selection")

        return selected_versioned, selected_repeatable

    @staticmethod
    def _select_by_patterns(migrations: list[Migration], patterns: list[str]) -> list[Migration]:
        if not patterns:
            return []

        selected: list[Migration] = []
        selected_names: set[str] = set()

        for migration in migrations:
            if any(fnmatch(migration.filename, pattern) for pattern in patterns):
                if migration.filename not in selected_names:
                    selected.append(migration)
                    selected_names.add(migration.filename)

        return selected

    def _replay_applied_versioned(self, migration: Migration) -> None:
        if not isinstance(self.adapter, DatabaseAdapter):
            raise RuntimeError("No valid DatabaseAdapter provided")

        adapter: DatabaseAdapter = self.adapter
        down_sql = migration.down_sql
        if not down_sql:
            raise RuntimeError(f"Replay requires -- ezmig:rollback section: {migration.filename}")

        logger.info(f"Replaying versioned migration: {migration.filename}")
        start = time.time()
        try:
            adapter.begin()
            adapter.execute(down_sql)
            adapter.execute(migration.apply_sql)
            migration.duration_ms = int((time.time() - start) * 1000)
            adapter.record_migration(migration)
            adapter.commit()
            logger.info(f"✔ Replayed {migration.filename} in {migration.duration_ms}ms")
        except Exception as error:
            adapter.rollback()
            if isinstance(error, SQLExecutionError):
                self._log_sql_execution_error(action="replay", migration=migration, error=error)
            else:
                logger.error(f"✖ Failed to replay {migration.filename}: {error}")
            raise

    def _apply_single(self, migration: Migration):
        """
        Apply a single migration transactionally.
        """
        if not isinstance(self.adapter, DatabaseAdapter):
            raise RuntimeError("No valid DatabaseAdapter provided")

        adapter: DatabaseAdapter = self.adapter  # type narrowing for ty

        logger.info(f"Applying {migration.type} migration: {migration.filename}")
        start = time.time()
        try:
            adapter.begin()
            adapter.execute(migration.apply_sql)
            migration.duration_ms = int((time.time() - start) * 1000)
            adapter.record_migration(migration=migration)
            adapter.commit()
            logger.info(f"✔ Applied {migration.filename} in {migration.duration_ms}ms")
        except Exception as e:
            adapter.rollback()
            if isinstance(e, SQLExecutionError):
                self._log_sql_execution_error(action="apply", migration=migration, error=e)
            else:
                logger.error(f"✖ Failed to apply {migration.filename}: {e}")
            raise

    def _log_sql_execution_error(
        self,
        *,
        action: str,
        migration: Migration,
        error: SQLExecutionError,
    ) -> None:
        logger.error(
            "✖ Failed to %s %s at statement %s/%s: %s\n--- SQL ---\n%s\n-----------",
            action,
            migration.filename,
            error.statement_index,
            error.total_statements,
            error,
            _truncate_sql(error.statement),
        )

    def rollback(self, steps=1):
        """
        Rollback the last `steps` applied versioned migrations in reverse order.
        Only migrations with a -- ezmig:rollback section can be rolled back.
        """

        if not isinstance(self.adapter, DatabaseAdapter):
            raise RuntimeError("No valid DatabaseAdapter provided")

        adapter: DatabaseAdapter = self.adapter

        # 1. get applied migrations from DB
        applied = adapter.migrations()

        if not applied:
            logger.info("No migrations to rollback")
            return

        # 2. take last N (only versioned)
        to_rollback = [m for m in applied[-steps:] if m.type == "versioned"]

        # 3. load all migration files
        all_files = {m.filename: m for m in self._load_versioned()}

        # 4. resolve DB migrations -> file migrations
        resolved = []
        for m in to_rollback:
            filename = m.filename
            if filename not in all_files:
                raise RuntimeError(f"Migration file not found for rollback: {filename}")
            resolved.append(all_files[filename])

        # 5. rollback in reverse order
        for migration in reversed(resolved):
            sql = migration.down_sql
            if not sql:
                logger.warning(f"No -- ezmig:rollback in {migration.filename}, skipping")
                continue

            logger.info(f"Rolling back {migration.filename}")
            try:
                adapter.begin()
                adapter.execute(sql)
                adapter.remove_migration(migration.checksum)
                adapter.commit()
            except Exception as error:
                adapter.rollback()
                if isinstance(error, SQLExecutionError):
                    self._log_sql_execution_error(action="rollback", migration=migration, error=error)
                raise

    def status(self) -> list[Migration]:
        if not isinstance(self.adapter, DatabaseAdapter):
            raise RuntimeError("No valid DatabaseAdapter provided")

        adapter: DatabaseAdapter = self.adapter
        adapter.ensure_schema()
        checksums = adapter.checksums()

        migrations = []

        # versioned
        for m in self._load_versioned():
            if m.checksum in checksums:
                m.state = MigrationState.APPLIED
            else:
                m.state = MigrationState.PENDING
            migrations.append(m)

        # repeatable
        for m in self._load_repeatable():
            if m.checksum in checksums:
                m.state = MigrationState.UNCHANGED
            else:
                m.state = MigrationState.CHANGED
            migrations.append(m)

        return migrations

    def validate(self) -> None:
        if not isinstance(self.adapter, DatabaseAdapter):
            raise RuntimeError("No valid DatabaseAdapter provided")

        adapter: DatabaseAdapter = self.adapter
        adapter.ensure_schema()

        disk_versioned = self._load_versioned()
        db_migrations = adapter.migrations()
        db_versioned = [m for m in db_migrations if m.type == "versioned"]

        errors: list[str] = []
        warnings: list[str] = []

        disk_by_name = {migration.filename: migration for migration in disk_versioned}

        for db_migration in db_versioned:
            disk_migration = disk_by_name.get(db_migration.filename)
            if disk_migration is None:
                errors.append(f"Applied migration missing on disk: {db_migration.filename}")
                continue

            if disk_migration.checksum != db_migration.checksum:
                errors.append(f"Checksum drift detected for migration: {db_migration.filename}")

        applied_versioned_names = {migration.filename for migration in db_versioned}
        saw_pending = False
        for migration in disk_versioned:
            if migration.filename in applied_versioned_names:
                if saw_pending:
                    errors.append(
                        "Out-of-order applied migration detected: "
                        f"{migration.filename} has lower pending migrations before it"
                    )
            else:
                saw_pending = True

        disk_repeatable = self._load_repeatable()
        db_repeatable = {m.filename: m for m in db_migrations if m.type == "repeatable"}
        for migration in disk_repeatable:
            stored = db_repeatable.get(migration.filename)
            if stored is not None and stored.checksum != migration.checksum:
                warnings.append(f"Repeatable changed since last apply: {migration.filename}")

        if warnings:
            for warning in warnings:
                logger.warning(warning)

        if errors:
            message = "Validation failed:\n" + "\n".join(f"- {error}" for error in errors)
            logger.error(message)
            raise RuntimeError(message)

        logger.info("Validation passed")
