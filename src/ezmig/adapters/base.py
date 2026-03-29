from abc import ABC, abstractmethod

from ezmig.migration import Migration


class DatabaseAdapter(ABC):
    @abstractmethod
    def ensure_schema(self) -> None:
        """Ensure the migrations table exists"""
        ...

    @abstractmethod
    def migrations(self) -> list[Migration]:
        """Return a list of applied versioned migrations as Migration instances, in order applied"""
        ...

    @abstractmethod
    def checksums(self) -> set[str]:
        """Return a list of checksums"""
        ...

    @abstractmethod
    def record_migration(self, migration: Migration) -> None:
        """Record that a migration has been applied (upsert by filename)."""
        ...

    @abstractmethod
    def remove_migration(self, migration_hash: str) -> None:
        """Remove a migration record by hash (for rollback)"""
        ...

    @abstractmethod
    def execute(self, sql: str) -> None:
        """Execute arbitrary SQL"""
        ...

    @abstractmethod
    def begin(self) -> None:
        """Begin transaction"""
        ...

    @abstractmethod
    def commit(self) -> None:
        """Commit transaction"""
        ...

    @abstractmethod
    def rollback(self) -> None:
        """Rollback transaction"""
        ...
