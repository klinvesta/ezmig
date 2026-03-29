import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_VERSIONED_PATH = Path("./migrations/versioned")
DEFAULT_REPEATABLE_PATH = Path("./migrations/repeatable")
CONFIG_FILE_NAME = "ezmig.toml"
DEFAULT_PROFILE_NAME = "default"
ENV_CONFIG_FILE = "EZMIG_CONFIG"
ENV_PROGRAMDATA = "PROGRAMDATA"
SECTION_DEFAULT = "default"
SECTION_MIGRATION = "migration"
SECTION_DATABASE = "database"
SECTION_GROUP = "group"
KEY_DATABASE = "database"
KEY_VERSIONED = "versioned"
KEY_REPEATABLE = "repeatable"
KEY_URL = "url"
KEY_CATEGORIES = "categories"
KEY_ALLOW_REPLAY = "allow_replay"
KEY_MEMBERS = "members"
KEY_FILTERS = "filters"


@dataclass(frozen=True)
class MigrationProfileConfig:
    """Configuration for a named set of migration paths."""

    versioned_paths: list[Path]
    repeatable_paths: list[Path]


@dataclass(frozen=True)
class DatabaseTargetConfig:
    """Configuration for a named database target."""

    name: str
    url: str
    migration: str
    categories: dict[str, str]
    allow_replay: bool = False


@dataclass(frozen=True)
class DatabaseGroupConfig:
    """Configuration for a named group of database targets."""

    name: str
    members: list[str] | None = None
    filters: dict[str, list[str]] | None = None


@dataclass(frozen=True)
class EZMigConfig:
    """Resolved multi-database configuration."""

    default_database: str | None
    migration: dict[str, MigrationProfileConfig]
    database: dict[str, DatabaseTargetConfig]
    group: dict[str, DatabaseGroupConfig]

    # Compatibility properties for legacy code
    @property
    def url(self) -> str:
        """For backward compatibility: return the URL of the default database."""
        if self.default_database and self.default_database in self.database:
            return self.database[self.default_database].url
        return ""

    @property
    def versioned_paths(self) -> list[Path]:
        """For backward compatibility: return versioned paths from the default database's migration profile."""
        if self.default_database and self.default_database in self.database:
            target = self.database[self.default_database]
            profile_name = target.migration
            if profile_name in self.migration:
                return self.migration[profile_name].versioned_paths
        # Fallback to defaults
        return [_normalize_path(DEFAULT_VERSIONED_PATH)]

    @property
    def repeatable_paths(self) -> list[Path]:
        """For backward compatibility: return repeatable paths from the default database's migration profile."""
        if self.default_database and self.default_database in self.database:
            target = self.database[self.default_database]
            profile_name = target.migration
            if profile_name in self.migration:
                return self.migration[profile_name].repeatable_paths
        # Fallback to defaults
        return [_normalize_path(DEFAULT_REPEATABLE_PATH)]

    @property
    def versioned_path(self) -> Path:
        """For backward compatibility: return first versioned path."""
        return self.versioned_paths[0]

    @property
    def repeatable_path(self) -> Path:
        """For backward compatibility: return first repeatable path."""
        return self.repeatable_paths[0]

    def resolve_database(
        self,
        name: str | None = None,
        categories: dict[str, str] | None = None,
        group: str | None = None,
    ) -> DatabaseTargetConfig:
        """
        Resolve a single database target based on selection criteria.

        Selection precedence:
        1. name (direct database name)
        2. categories (filter by category key-value pairs)
        3. group (named group)
        4. default_database (configured default)

        Raises ValueError if resolution is ambiguous or fails.
        """
        candidates: list[str] = []

        if name:
            if name not in self.database:
                available = ", ".join(self.database.keys())
                raise ValueError(f"Database '{name}' not found. Available: {available}")
            candidates = [name]
        elif categories:
            candidates = self._filter_by_categories({k: [v] for k, v in categories.items()})
        elif group:
            if group not in self.group:
                available = ", ".join(self.group.keys())
                raise ValueError(f"Group '{group}' not found. Available: {available}")
            group_config = self.group[group]
            if group_config.members:
                candidates = group_config.members
            elif group_config.filters:
                candidates = self._filter_by_categories(group_config.filters)
        elif self.default_database:
            candidates = [self.default_database]

        if not candidates:
            raise ValueError(
                "No database target found. Provide --database, --category, --group, or set [default].database"
            )

        if len(candidates) > 1:
            raise ValueError(
                f"Ambiguous target selection matched {len(candidates)} databases: {', '.join(candidates)}"
            )

        return self.database[candidates[0]]

    def _filter_by_categories(self, filters: dict[str, list[str]]) -> list[str]:
        """
        Filter database targets by category.

        Logic: AND across keys, OR within each key's values.
        E.g., {env: ["dev", "uat"], location: ["uk"]} matches
        databases with (env=dev OR env=uat) AND location=uk
        """
        matching: list[str] = []

        for db_name, db_target in self.database.items():
            match = True
            for key, values in filters.items():
                # If the key is not in this target's categories, it doesn't match
                if key not in db_target.categories:
                    match = False
                    break
                # If the target's value for this key is not in the allowed values, it doesn't match
                if db_target.categories[key] not in values:
                    match = False
                    break
            if match:
                matching.append(db_name)

        return matching


def _load_dotenv(dotenv_path: Path) -> None:
    """Load a .env file into os.environ without overriding already-set variables."""
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip optional inline comment
        if " #" in value:
            value = value[: value.index(" #")].rstrip()
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def _normalize_path(path: Path) -> Path:
    path = Path(os.path.expandvars(str(path)))
    if path.is_absolute():
        return path
    return (Path.cwd() / path).resolve()


def _normalize_path_from_base(path: Path, base_dir: Path) -> Path:
    expanded = Path(os.path.expandvars(str(path)))
    if expanded.is_absolute():
        return expanded
    return (base_dir / expanded).resolve()


def _expand_env_vars(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [_expand_env_vars(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env_vars(item) for key, item in value.items()}
    return value


def _as_path_list(value: Any, default: Path) -> list[Path]:
    if value is None:
        return [default]

    if isinstance(value, str):
        return [_normalize_path(Path(value))]

    if isinstance(value, list):
        paths = [_normalize_path(Path(item)) for item in value if isinstance(item, str)]
        if paths:
            return paths

    return [_normalize_path(default)]


def _as_path_list_from_base(value: Any, default: Path, base_dir: Path) -> list[Path]:
    if value is None:
        return [_normalize_path_from_base(default, base_dir)]

    if isinstance(value, str):
        return [_normalize_path_from_base(Path(value), base_dir)]

    if isinstance(value, list):
        paths = [
            _normalize_path_from_base(Path(item), base_dir)
            for item in value
            if isinstance(item, str)
        ]
        if paths:
            return paths

    return [_normalize_path_from_base(default, base_dir)]


def _merge_sections(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict):
            merged[key] = dict(value)
        else:
            merged[key] = value
    return merged


def _discover_config_files(
    config_file: Path | None = None,
    config_dir: Path | None = None,
    include_user: bool = True,
    include_system: bool = True,
    existing_only: bool = True,
) -> list[Path]:
    discovered: list[Path] = []

    if include_system:
        if sys.platform.startswith("win"):
            program_data = Path(os.environ.get(ENV_PROGRAMDATA, "C:/ProgramData"))
            discovered.append(program_data / "ezmig" / CONFIG_FILE_NAME)
        else:
            discovered.extend(
                [
                    Path("/etc/ezmig") / CONFIG_FILE_NAME,
                    Path("/usr/local/etc/ezmig") / CONFIG_FILE_NAME,
                ]
            )

    if include_user:
        home = Path.home()
        discovered.extend(
            [home / ".ezmig" / "config.toml", home / ".config" / "ezmig" / CONFIG_FILE_NAME]
        )

    if config_dir is not None:
        discovered.append((config_dir / CONFIG_FILE_NAME).resolve())
    else:
        discovered.append((Path.cwd() / CONFIG_FILE_NAME).resolve())

    env_config = os.getenv(ENV_CONFIG_FILE)
    if env_config:
        discovered.append(Path(env_config).expanduser().resolve())

    if config_file is not None:
        discovered.append(config_file.resolve())

    ordered: list[Path] = []
    for path in discovered:
        if existing_only and not path.exists():
            continue
        if path not in ordered:
            ordered.append(path)

    return ordered


def get_config_files(
    *,
    config_file: Path | None = None,
    config_dir: Path | None = None,
    include_user: bool = True,
    include_system: bool = True,
    existing_only: bool = True,
) -> list[Path]:
    """Return discovered config files in load order (lowest precedence to highest)."""
    return _discover_config_files(
        config_file=config_file,
        config_dir=config_dir,
        include_user=include_user,
        include_system=include_system,
        existing_only=existing_only,
    )


def _load_merged_data(config_files: list[Path]) -> dict[str, Any]:
    merged: dict[str, Any] = {}

    for config_file in config_files:
        raw_data = tomllib.loads(config_file.read_text(encoding="utf-8"))
        data = _expand_env_vars(raw_data)
        base_dir = config_file.parent

        default_section = data.get(SECTION_DEFAULT, {})
        default_database = (
            default_section.get(KEY_DATABASE)
            if isinstance(default_section, dict) and default_section.get(KEY_DATABASE)
            else None
        )

        migration_section: dict[str, dict[str, Any]] = {}
        migration_data = data.get(SECTION_MIGRATION, {})
        if isinstance(migration_data, dict):
            for profile_name, profile_config in migration_data.items():
                if not isinstance(profile_config, dict):
                    continue
                migration_section[profile_name] = {
                    KEY_VERSIONED: _as_path_list_from_base(
                        profile_config.get(KEY_VERSIONED), DEFAULT_VERSIONED_PATH, base_dir
                    ),
                    KEY_REPEATABLE: _as_path_list_from_base(
                        profile_config.get(KEY_REPEATABLE), DEFAULT_REPEATABLE_PATH, base_dir
                    ),
                }

        database_section: dict[str, dict[str, Any]] = {}
        database_data = data.get(SECTION_DATABASE, {})
        if isinstance(database_data, dict):
            for db_name, db_config in database_data.items():
                if isinstance(db_config, dict):
                    database_section[db_name] = dict(db_config)

        group_section: dict[str, dict[str, Any]] = {}
        group_data = data.get(SECTION_GROUP, {})
        if isinstance(group_data, dict):
            for group_name, group_config in group_data.items():
                if isinstance(group_config, dict):
                    group_section[group_name] = dict(group_config)

        if default_database:
            merged["default_database"] = default_database

        merged[SECTION_MIGRATION] = _merge_sections(
            merged.get(SECTION_MIGRATION, {}), migration_section
        )
        merged[SECTION_DATABASE] = _merge_sections(
            merged.get(SECTION_DATABASE, {}), database_section
        )
        merged[SECTION_GROUP] = _merge_sections(merged.get(SECTION_GROUP, {}), group_section)

    return merged


def load_config(
    *,
    config_file: Path | None = None,
    config_dir: Path | None = None,
    include_user: bool = True,
    include_system: bool = True,
) -> EZMigConfig:
    """Load and parse layered ezmig config files, returning a resolved EZMigConfig."""
    _load_dotenv(Path(".env"))

    config_files = _discover_config_files(
        config_file=config_file,
        config_dir=config_dir,
        include_user=include_user,
        include_system=include_system,
        existing_only=True,
    )

    if not config_files:
        # Return minimal default config
        default_profile = MigrationProfileConfig(
            versioned_paths=[_normalize_path(DEFAULT_VERSIONED_PATH)],
            repeatable_paths=[_normalize_path(DEFAULT_REPEATABLE_PATH)],
        )
        return EZMigConfig(
            default_database=None,
            migration={DEFAULT_PROFILE_NAME: default_profile},
            database={},
            group={},
        )

    data = _load_merged_data(config_files)
    default_database = data.get("default_database")

    # Parse [migration.<name>] sections
    migration_dict = {}
    migration_data = data.get(SECTION_MIGRATION, {})
    if isinstance(migration_data, dict):
        for profile_name, profile_config in migration_data.items():
            if isinstance(profile_config, dict):
                versioned = profile_config.get(KEY_VERSIONED)
                repeatable = profile_config.get(KEY_REPEATABLE)

                if not isinstance(versioned, list) or not all(
                    isinstance(path, Path) for path in versioned
                ):
                    versioned = _as_path_list(
                        profile_config.get(KEY_VERSIONED), DEFAULT_VERSIONED_PATH
                    )

                if not isinstance(repeatable, list) or not all(
                    isinstance(path, Path) for path in repeatable
                ):
                    repeatable = _as_path_list(
                        profile_config.get(KEY_REPEATABLE), DEFAULT_REPEATABLE_PATH
                    )

                migration_dict[profile_name] = MigrationProfileConfig(
                    versioned_paths=versioned, repeatable_paths=repeatable
                )

    # Ensure at least a 'default' migration profile exists
    if DEFAULT_PROFILE_NAME not in migration_dict:
        migration_dict[DEFAULT_PROFILE_NAME] = MigrationProfileConfig(
            versioned_paths=[_normalize_path(DEFAULT_VERSIONED_PATH)],
            repeatable_paths=[_normalize_path(DEFAULT_REPEATABLE_PATH)],
        )

    # Parse [database.<name>] sections
    database_dict = {}
    database_data = data.get(SECTION_DATABASE, {})
    if isinstance(database_data, dict):
        for db_name, db_config in database_data.items():
            if isinstance(db_config, dict):
                url = db_config.get(KEY_URL, "")
                if not url:
                    raise ValueError(f"Database '{db_name}' missing required 'url' field")
                migration_profile = db_config.get(SECTION_MIGRATION, DEFAULT_PROFILE_NAME)
                categories = db_config.get(KEY_CATEGORIES, {})
                if not isinstance(categories, dict):
                    categories = {}
                allow_replay = db_config.get(KEY_ALLOW_REPLAY, False)
                if not isinstance(allow_replay, bool):
                    allow_replay = False
                database_dict[db_name] = DatabaseTargetConfig(
                    name=db_name,
                    url=url,
                    migration=migration_profile,
                    categories=categories,
                    allow_replay=allow_replay,
                )

    # Parse [group.<name>] sections
    group_dict = {}
    group_data = data.get(SECTION_GROUP, {})
    if isinstance(group_data, dict):
        for group_name, group_config in group_data.items():
            if isinstance(group_config, dict):
                members = group_config.get(KEY_MEMBERS)
                filters = group_config.get(KEY_FILTERS)
                group_dict[group_name] = DatabaseGroupConfig(
                    name=group_name, members=members, filters=filters
                )

    config = EZMigConfig(
        default_database=default_database,
        migration=migration_dict,
        database=database_dict,
        group=group_dict,
    )

    # Validate the complete config
    _validate_config(config)

    return config


def _validate_config(config: EZMigConfig) -> None:
    """Validate EZMigConfig for consistency and completeness."""
    errors = []

    # Check for duplicate database names (already enforced by dict keys, but be explicit)
    db_names = list(config.database.keys())
    if len(db_names) != len(set(db_names)):
        errors.append("Duplicate database names found")

    # Check that every database has a non-empty URL
    for db_name, db_target in config.database.items():
        if not db_target.url or not db_target.url.strip():
            errors.append(f"Database '{db_name}' has empty URL")

    # Check that every database's migration profile exists
    for db_name, db_target in config.database.items():
        if db_target.migration not in config.migration:
            errors.append(
                f"Database '{db_name}' references unknown migration profile '{db_target.migration}'"
            )

    # Check that every group member exists
    for group_name, group_target in config.group.items():
        if group_target.members:
            for member in group_target.members:
                if member not in config.database:
                    errors.append(
                        f"Group '{group_name}' references unknown database member '{member}'"
                    )

    # Check that group has exactly one selector mechanism
    for group_name, group_target in config.group.items():
        has_members = group_target.members is not None
        has_filters = group_target.filters is not None
        if not (has_members ^ has_filters):  # XOR: exactly one must be true
            errors.append(f"Group '{group_name}' must define exactly one of 'members' or 'filters'")

    if errors:
        raise ValueError("Config validation failed:\n  " + "\n  ".join(errors))
