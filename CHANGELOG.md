# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.23] - 2026-02-09

### Added

- **Search**: Intent-driven retrieval with 4 classifiers (EntityLookup, Temporal, AspectFilter, SemanticSearch)
- **Graph**: Real-time knowledge graph edge creation and neighbor query API (`GET /graph/neighbors`)
- **Graph**: Multi-hop path finding with BFS (max depth 3) and API endpoint (`GET /graph/paths`)
- **Entity Resolution**: Canonical subject/object dual-field scheme with 30+ built-in aliases
- **Retrieval**: Graph-enhanced retrieval with `smart_search()` and related-items context block
- **Aspect**: Expanded categories from 6 to 8 (added `identity` and `behaviors`)
- **Reified Statements**: Meta-facts about items (`meta_about` field), API endpoints `GET/POST /v2/items/{id}/meta`
- **Confidence Propagation**: Weekly pipeline neighbor-weighted algorithm (0.85 self + 0.15 neighbor signal)
- **Embedding Auto-Update**: `extract_and_store()` auto-generates embeddings; `recompute_all_embeddings()` batch rebuild

### Fixed

- **API**: `/health` endpoint now returns dynamic `app.version` instead of hardcoded `"0.1.0"`
- **SurrealDB**: `delete_stale()` uses `RecordID` objects instead of strings for correct `NOT IN` comparison

## [0.1.22] - 2026-02-06

### Fixed

- **Desktop**: Fix Windows service startup failure caused by backslash in SurrealDB `file://` URL path
- **Desktop**: Add pre-spawn check for Python binary with actionable error message

## [0.1.21] - 2026-02-06

### Changed

- **Classification System**: Refactored to use `item.category` as single source of truth
  - Categories are now derived from items via `list_distinct_categories()` instead of preset `category` table
  - `ensure_default_categories()` converted to no-op; `category` table retained as summary cache only
  - `/categories`, `/retrieve`, `/v2/categories`, `/v2/stats` endpoints updated
  - `gather_category_stats` (both SQLAlchemy and UoW versions), `get_category_stats`, `get_memory_stats` updated
  - `migrate_backend.py` verification counts updated

## [0.1.20] - 2026-02-05

### Added

- **Desktop**: Status page now displays both App version (from Tauri) and API version (from backend)
- **Desktop**: Added Tauri v2 capabilities configuration for app API permissions

## [0.1.19] - 2026-02-05

### Changed

- **Desktop**: Minimize-to-tray animation now targets actual tray icon position
  - Uses `TrayIcon::rect()` API to get tray icon coordinates
  - Previously hardcoded to screen top-right corner, now animates to menu bar where icon actually is

## [0.1.18] - 2026-02-04

### Fixed

- **Desktop UI**: Selected memory item text unreadable in dark theme
  - Root cause: `--color-muted` and `--color-muted-foreground` were set to same color (`#64748b`)
  - Fixed: `--color-muted: #1e293b` (dark bg), `--color-muted-foreground: #94a3b8` (light text)
  - Updated selected item styling to use `bg-white/10` + green left border

## [0.1.17] - 2026-02-04

### Fixed

- **Desktop**: Window not showing on top at startup - added `window.show()` and `window.set_focus()` when starting in visible mode

## [0.1.16] - 2026-02-04

### Fixed

- **Desktop UI**: Memory detail panel content overflow fixed - content now scrolls within rounded card instead of overflowing

## [0.1.15] - 2026-02-04

### Changed

- **Release artifact naming**: Clearer platform naming convention
  - `Kiroku.Memory_X.X.X_macos_arm64.dmg` (Apple Silicon)
  - `Kiroku.Memory_X.X.X_macos_x64.dmg` (Intel)
  - `Kiroku.Memory_X.X.X_windows_x64.msi`
  - `Kiroku.Memory_X.X.X_linux_x64.AppImage`

### Fixed

- Version number now correctly shows in release artifacts

## [0.1.14] - 2026-02-04

### Added

- **Internationalization (i18n)**: Desktop app now supports multiple languages
  - English (default fallback)
  - Japanese (日本語)
  - Traditional Chinese (繁體中文)
  - Auto-detection: Chinese systems → zh-TW, Japanese → ja, others → en
  - Date formatting localized per language
  - Dev mode language switching via `window.__i18n__.changeLanguage()`

### Changed

- All UI text extracted to JSON translation files
- Date display uses locale-aware formatting

## [0.1.13] - 2026-02-02

### Added

- **macOS Code Signing**: App is now signed with Apple Developer ID certificate
  - Eliminates "app is damaged" and Gatekeeper warnings
  - Users no longer need to run `xattr -cr` or right-click to open
- **macOS Notarization**: App is notarized by Apple for enhanced security
  - Smooth installation experience on macOS 10.14.5+

## [0.1.12] - 2026-02-02

### Fixed

- **macOS App Nap**: Disable App Nap to prevent service becoming unresponsive when app is in background
  - Added `NSAppSleepDisabled`, `NSSupportsAutomaticTermination`, `NSSupportsSuddenTermination` to Info.plist

### Changed

- **Maintenance page**: Toggle start/stop button based on service status
- **Sidebar**: Improved visual balance for Kiroku label spacing

## [0.1.11] - 2026-02-02

### Added

- **Desktop App**: Cross-platform standalone application (macOS, Windows, Linux)
  - No Docker, Python, or database setup required
  - Embedded SurrealDB for local data storage
  - Secure API key storage via macOS Keychain / Windows Credential Manager
  - Same REST API at `http://127.0.0.1:8000`
- **GitHub Actions Release Workflow**: Automated multi-platform builds
  - macOS (Apple Silicon + Intel)
  - Windows x64
  - Linux x64 (AppImage)
- **macOS launch instructions**: Added documentation for unsigned app first launch
  - `xattr -cr` command for "damaged app" error
  - Right-click → Open for Gatekeeper bypass

### Fixed

- **CI/CD**: `.gitignore` rule `lib/` was ignoring all `lib/` directories including `desktop/src/lib/`
  - Changed to `/lib/` to only ignore root-level directory
- **CI/CD**: macOS and Linux sed syntax differences causing build failures
  - Separated platform-specific sed commands in workflow
- **CI/CD**: Missing `once_cell` dependency for non-macOS credential storage fallback

### Changed

- Installation guide restructured with Desktop App as recommended option
- README files updated with prominent "3 Steps to Get Started" section

## [0.1.0] - 2026-01-15

### Added

- Initial release of Kiroku Memory
- Core features:
  - Append-only raw logs with immutable provenance tracking
  - Atomic facts extraction via LLM (subject-predicate-object)
  - Category-based organization with 6 default categories
  - Tiered retrieval (summaries first, drill down to facts)
  - Conflict resolution with automatic contradiction detection
  - Time decay for memory confidence
  - Vector search with pgvector
  - Knowledge graph relationship mapping
- Claude Code Skill integration:
  - SessionStart hook for auto-loading memory context
  - Stop hook for two-phase memory capture (Fast regex + Slow LLM)
  - PostToolUse hook for incremental capture during long conversations
  - `/remember`, `/recall`, `/forget`, `/memory-status` commands
- Dual backend support:
  - PostgreSQL + pgvector (production)
  - SurrealDB (embedded/desktop)
- Maintenance jobs:
  - Nightly: merge duplicates, promote hot memories
  - Weekly: time decay, archive old items
  - Monthly: rebuild embeddings and knowledge graph
- Full REST API with OpenAPI documentation
- Structured logging, metrics, and health checks

[0.1.16]: https://github.com/yelban/kiroku-memory/compare/v0.1.15...v0.1.16
[0.1.15]: https://github.com/yelban/kiroku-memory/compare/v0.1.14...v0.1.15
[0.1.14]: https://github.com/yelban/kiroku-memory/compare/v0.1.13...v0.1.14
[0.1.13]: https://github.com/yelban/kiroku-memory/compare/v0.1.12...v0.1.13
[0.1.12]: https://github.com/yelban/kiroku-memory/compare/v0.1.11...v0.1.12
[0.1.11]: https://github.com/yelban/kiroku-memory/compare/v0.1.0...v0.1.11
[0.1.0]: https://github.com/yelban/kiroku-memory/releases/tag/v0.1.0
