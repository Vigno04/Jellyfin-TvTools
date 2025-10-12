# Playlist Management

## Unified Configuration

The app now uses a **single consolidated list** for all playlist URLs instead of maintaining separate fields.

### How It Works

1. **Settings → Saved playlist URLs**
   - One URL per line (multiline text field)
   - The **first URL** is automatically used for the "Download playlist" button
   - All URLs are loaded when clicking "Load saved playlists"

2. **Dashboard Buttons**
   - **Download playlist**: Loads the first saved URL (or whatever you type in the URL field)
   - **Load saved playlists**: Bulk-loads all URLs from your saved list in one operation

### Migration from Old Config

If you have an existing `download_url` in your config:
- The settings panel automatically migrates it to the top of `saved_playlists`
- Both fields are kept in sync: saving settings updates `download_url` to match the first saved playlist
- This ensures backward compatibility with any external tools or scripts

### Example Configuration

```json
{
  "saved_playlists": [
    "https://example.com/primary.m3u",
    "https://backup-provider.tv/list.m3u",
    "https://local-server/custom.m3u"
  ]
}
```

### Benefits

- **Less confusion**: One place to manage all your playlist sources
- **Quick reload**: One button to refresh everything
- **Flexible workflow**: Single download for testing, bulk load for production
- **Backward compatible**: Existing configs are automatically migrated

### Usage Tips

- Keep your most reliable source as the first URL for quick single downloads
- Add backup sources below for redundancy
- The "Load saved playlists" button is disabled until you have at least one saved URL
- Button state updates immediately after saving settings
