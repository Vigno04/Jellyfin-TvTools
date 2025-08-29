# Jellyfin TV Tools - Modern GUI Version

A modern, cross-platform GUI application for managing IPTV M3U playlists for Jellyfin Media Server.

## Features

🎯 **Modern Interface**: Built with Flet for a sleek, native-looking UI on Windows and Linux  
📺 **Smart Channel Management**: Automatic quality prioritization (4K > HD > Standard)  
🔍 **Advanced Filtering**: Search, group-based filtering, and manual selection  
⚙️ **Configurable**: JSON-based configuration with sensible defaults  
🎨 **Theme Support**: System theme integration (dark/light mode)  
📱 **Cross-Platform**: Works on Windows, Linux, and can run as web app  

## Quick Start

### Windows
1. Double-click `run_gui.bat`
2. The application will automatically install dependencies and start

### Linux/Manual Start
1. Install Python 3.8+ if not already installed
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python jellyfin_tv_tools.py`

## How to Use

### 1. Load Channels
- Enter your M3U playlist URL (default is pre-configured)
- Click "Load Channels" to download and parse the playlist
- The app will automatically apply quality management and filtering

### 2. Select Channels
- Browse the list of available channels
- Use the search box to find specific channels
- Select/deselect individual channels or use "Select All"/"Select None"
- Channels are organized by groups (RAI, Mediaset, etc.)

### 3. Export Playlist
- Click "Export Selected Channels"
- The filtered M3U file will be saved as `tivustream_list.m3u`
- Import this file into Jellyfin's Live TV setup

## Configuration

Edit `config.json` to customize:

- **Source URLs**: Change the default M3U playlist source
- **Channel Groups**: Specify which channel groups to keep/exclude  
- **Quality Management**: Configure 4K/HD prioritization
- **Channel Lists**: Force include/exclude specific channels
- **Patterns**: Use regex patterns for advanced filtering

## Project Structure

```
Jellyfin-TvTools/
├── jellyfin_tv_tools.py    # Main launcher
├── run_gui.bat             # Windows launcher
├── requirements.txt        # Python dependencies
├── config.json            # Application configuration
├── src/
│   ├── backend/
│   │   └── m3u_processor.py # M3U processing logic
│   └── ui/
│       └── main_app.py     # Flet GUI application
├── tivustream_list.m3u     # Generated playlist (output)
└── update_channels.py      # Legacy CLI version
```

## Legacy CLI Version

The original command-line version is still available:
- Run: `python update_channels.py` or `update_channels.bat`
- Same functionality, but text-based interface

## Requirements

- Python 3.8 or higher
- Internet connection for downloading playlists
- ~10MB disk space for dependencies

## Technical Details

- **Backend**: Pure Python with requests for HTTP operations
- **Frontend**: Flet (Flutter for Python) for modern UI
- **Configuration**: JSON-based settings
- **Export Format**: Standard M3U playlist compatible with Jellyfin

## Contributing

This project is designed to be easily extensible:
- Backend logic is separated in `src/backend/`
- UI components are modular in `src/ui/`
- Configuration is externalized in `config.json`

## License

See LICENSE file for details.

---

**Enjoy your streamlined IPTV management experience! 🎉**
