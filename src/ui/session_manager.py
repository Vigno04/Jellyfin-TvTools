#!/usr/bin/env python3
"""Complete session management for channels and selections."""
import os
import json
from typing import List, Dict, Any, Optional

try:  # Support package import and legacy direct import
    from ..backend.config_manager import get_output_path, ensure_output_directory_exists  # type: ignore
except ImportError:  # Fallback
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from config_manager import get_output_path, ensure_output_directory_exists  # type: ignore

class SessionManager:
    def __init__(self, data_dir: str = "data", config: Dict[str, Any] = None):
        self.data_dir = data_dir
        self.config = config or {}
        
        # Use config-based path if config is provided, otherwise use legacy path
        if self.config:
            self.session_file = get_output_path(self.config, "current_session")
            ensure_output_directory_exists(self.config, "current_session")
        else:
            self.session_file = os.path.join(data_dir, "session.json")
            os.makedirs(data_dir, exist_ok=True)

    def save_session(self, channels: List[Dict[str, Any]], playlist_sources: List[Dict], 
                     stream_urls_seen: set, url_field: str = ""):
        """Save complete session state including all channels and selections."""
        try:
            session_data = {
                "channels": channels,
                "playlist_sources": playlist_sources,
                "stream_urls_seen": list(stream_urls_seen),
                "url_field": url_field,
                "version": "1.0"
            }
            
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Failed to save session: {e}")
            return False

    def load_session(self) -> Optional[Dict[str, Any]]:
        """Load complete session state."""
        try:
            if not os.path.exists(self.session_file):
                return None
                
            with open(self.session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            
            # Convert stream_urls_seen back to set
            if "stream_urls_seen" in session_data:
                session_data["stream_urls_seen"] = set(session_data["stream_urls_seen"])
            
            return session_data
        except Exception as e:
            print(f"Failed to load session: {e}")
            return None

    def clear_session(self):
        """Clear saved session."""
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
            return True
        except Exception:
            return False

    def has_saved_session(self) -> bool:
        """Check if there's a saved session."""
        return os.path.exists(self.session_file) and os.path.getsize(self.session_file) > 0
