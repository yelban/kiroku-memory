# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **macOS App Nap**: Disable App Nap to prevent service becoming unresponsive when app is in background
  - Added `NSAppSleepDisabled`, `NSSupportsAutomaticTermination`, `NSSupportsSuddenTermination` to Info.plist

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

[0.1.11]: https://github.com/yelban/kiroku-memory/compare/v0.1.0...v0.1.11
[0.1.0]: https://github.com/yelban/kiroku-memory/releases/tag/v0.1.0
