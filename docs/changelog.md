# Changelog

All notable changes to EZMig are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
EZMig uses [semantic versioning](https://semver.org/).

---

## [Unreleased]

### Added

- MkDocs documentation framework
- GitHub Actions release workflow (`.github/workflows/release.yml`)

### Changed

- `-- ezmig:apply` and `-- ezmig:rollback` sections can now appear in **any order** within a migration file; EZMig locates each section by marker offset rather than relying on a fixed sequence

---

## [0.1.0] — 2026-03-24

### Added

- Versioned migrations with lexicographic ordering
- Repeatable migrations with checksum tracking
- `ezmig apply`, `ezmig plan`, `ezmig status`, `ezmig validate`, `ezmig rollback`, `ezmig new`
- SQLite, PostgreSQL, and Oracle adapter support
- Transaction support where available
- `-- ezmig:rollback` block support
- `ezmig_migrations` tracking table
- `ezmig.toml` configuration with multi-directory repeatable support
- CLI scaffolding via `ezmig new`
