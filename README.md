
# Jellyfin TV Tools

> **Modern cross-platform GUI for managing IPTV M3U playlists for Jellyfin Media Server**

---

## 🚀 Quick Start

- **Windows:** Double-click `run.bat`
- **Linux/Manual:** Run `python run.py`

## ✨ Features

- **Modern Flet-based GUI** (Windows/Linux, dark/light theme)
- **Multi-playlist management:** Download, merge, and filter multiple M3U sources
- **Smart channel filtering:** Keep/exclude by group, name, or pattern
- **Advanced quality management:** Merge duplicates by name/quality, probe stream quality
- **Manual & bulk selection:** Search, select, and optimize channels
- **Session management:** Auto-save/restore, backup, and import/export selections
- **Configurable:** All settings in `src/config.json` (playlist URLs, filters, quality, output paths)
- **Export/Import:** Save playlists, channel lists, and session backups
- **Test scripts:** For normalization and merging logic

## 🖥️ GUI Overview

- **Sources:** Add playlist URLs, load all saved sources, refresh/clear
- **Channels:** Search, select, filter, and group channels
- **Quality:** Merge duplicates, remove dead/unwanted streams, optimize
- **Export/Backup:** Export playlist, session, or channel list; restore/import
- **Settings:** Edit all config options in-app (slide-out panel)

## 🛠️ Project Structure

```
Jellyfin-TvTools/
├── run.py                # Main application launcher
├── run.bat               # Windows launcher
├── src/
│   ├── config.json       # Main configuration (playlists, filters, quality)
│   ├── requirements.txt  # Python dependencies (Flet, requests)
│   ├── backend/          # Core logic: download, parse, filter, merge, export
│   └── ui/               # Flet GUI, mixins, and helpers
├── data/                 # Generated playlists, session, and backups
├── test_merge_debug.py   # Test: channel merging/normalization
├── test_normalize.py     # Test: normalization logic
└── PLAYLIST_MANAGEMENT.md# Details on playlist config and migration
```

## ⚙️ Configuration

- **Edit `src/config.json`** or use the in-app settings panel
- Manage playlist URLs, filtering rules, quality priorities, and output paths
- See [`PLAYLIST_MANAGEMENT.md`](PLAYLIST_MANAGEMENT.md) for playlist config details

## 🧩 Requirements

- Python 3.9+
- [Flet](https://flet.dev/) (auto-installed)
- requests (auto-installed)

## 🧪 Testing & Debugging

- `test_merge_debug.py`: Test merging/normalization of channel names
- `test_normalize.py`: Test normalization/grouping logic

## 📦 Installation

No manual install needed—dependencies are auto-installed on first run.

## 📚 Documentation

- See in-app tooltips and settings for guidance
- Playlist config and migration: [`PLAYLIST_MANAGEMENT.md`](PLAYLIST_MANAGEMENT.md)

---
**Jellyfin TV Tools** is open source and not affiliated with Jellyfin. For issues or suggestions, open an issue on GitHub.
