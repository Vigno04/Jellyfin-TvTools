# Changelog

All notable changes to Jellyfin TV Tools will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Build system for creating Windows and Linux executables
- GitHub Actions workflow for automated releases
- Release guide documentation

## [1.0.0] - 2025-10-14

### Added
- Modern Flet-based GUI for IPTV playlist management
- Multi-playlist download and merging support
- Smart channel filtering by group, name, and patterns
- Advanced quality management with duplicate merging
- Stream quality probing and dead link checking
- Manual and bulk channel selection
- Search functionality across channels
- Session management with auto-save/restore
- Backup and import/export capabilities
- Configurable settings via `config.json`
- In-app settings editor with slide-out panel
- Dark/light theme support
- Cross-platform support (Windows/Linux)
- Playlist URL management
- Group-based organization
- Export to M3U format
- Session and channel list backup

### Features
- **Sources Tab**: Add/remove playlist URLs, load from config, refresh
- **Channels Tab**: Browse, search, select/deselect channels
- **Quality Tab**: Merge duplicates, optimize quality, remove dead streams
- **Export/Import**: Save playlists, backup sessions, restore from backup
- **Settings**: Edit all configuration options in-app

### Technical
- Built with Flet framework for cross-platform GUI
- Modular backend architecture
- Async operations for non-blocking UI
- JSON-based configuration and session storage
- M3U parser with quality detection
- Stream quality checker with configurable timeout

---

## Release Types

- **Major version (x.0.0)**: Breaking changes, major rewrites
- **Minor version (0.x.0)**: New features, backwards compatible
- **Patch version (0.0.x)**: Bug fixes, minor improvements

---

## Template for New Releases

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Security fixes
```
