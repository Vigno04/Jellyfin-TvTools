#!/usr/bin/env python3
"""Complete session management for channels and selections."""
import os
import json
import logging
from typing import List, Dict, Any, Optional

try:  # Support package import and legacy direct import
    from ..backend.config_manager import get_output_path, ensure_output_directory_exists  # type: ignore
except ImportError:  # Fallback
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
    from config_manager import get_output_path, ensure_output_directory_exists  # type: ignore

# Configure logging
logger = logging.getLogger(__name__)

# Session file version for compatibility checks
SESSION_VERSION = "1.0"

class SessionManager:
    """Manages persistent session state for IPTV channel selections."""
    
    def __init__(self, data_dir: str = "data", config: Optional[Dict[str, Any]] = None):
        """
        Initialize the session manager.
        
        Args:
            data_dir: Directory for storing session files (default: "data")
            config: Optional configuration dictionary for output path settings
        """
        self.data_dir = data_dir
        self.config = config or {}
        
        # Use config-based path if config is provided, otherwise use legacy path
        if self.config:
            self.session_file = get_output_path(self.config, "current_session")
            ensure_output_directory_exists(self.config, "current_session")
        else:
            self.session_file = os.path.join(data_dir, "session.json")
            os.makedirs(data_dir, exist_ok=True)

    def save_session(
        self, 
        channels: List[Dict[str, Any]], 
        playlist_sources: List[Dict], 
        stream_urls_seen: set, 
        url_field: str = ""
    ) -> bool:
        """
        Save complete session state including all channels and selections.
        
        Args:
            channels: List of channel dictionaries with metadata
            playlist_sources: List of loaded playlist source information
            stream_urls_seen: Set of already-seen stream URLs to avoid duplicates
            url_field: Current URL field value
            
        Returns:
            True if save was successful, False otherwise
        """
        try:
            session_data = {
                "channels": channels,
                "playlist_sources": playlist_sources,
                "stream_urls_seen": list(stream_urls_seen),
                "url_field": url_field,
                "version": SESSION_VERSION
            }
            
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Session saved successfully to {self.session_file}")
            return True
            
        except (IOError, OSError) as e:
            logger.error(f"Failed to save session (IO error): {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to save session (unexpected error): {e}")
            return False

    def load_session(self) -> Optional[Dict[str, Any]]:
        """
        Load complete session state from disk.
        
        Returns:
            Dictionary with session data if successful, None otherwise
        """
        try:
            if not os.path.exists(self.session_file):
                logger.info("No saved session file found")
                return None
                
            with open(self.session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            
            # Validate session version
            if session_data.get("version") != SESSION_VERSION:
                logger.warning(
                    f"Session version mismatch: expected {SESSION_VERSION}, "
                    f"got {session_data.get('version')}"
                )
            
            # Convert stream_urls_seen back to set
            if "stream_urls_seen" in session_data:
                session_data["stream_urls_seen"] = set(session_data["stream_urls_seen"])
            
            logger.info(f"Session loaded successfully from {self.session_file}")
            return session_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to load session (invalid JSON): {e}")
            return None
        except (IOError, OSError) as e:
            logger.error(f"Failed to load session (IO error): {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load session (unexpected error): {e}")
            return None

    def clear_session(self) -> bool:
        """
        Clear saved session by deleting the session file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
                logger.info(f"Session cleared: {self.session_file}")
            return True
        except (IOError, OSError) as e:
            logger.error(f"Failed to clear session: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to clear session (unexpected error): {e}")
            return False

    def has_saved_session(self) -> bool:
        """
        Check if there's a valid saved session available.
        
        Returns:
            True if session file exists and has content, False otherwise
        """
        try:
            return (
                os.path.exists(self.session_file) and 
                os.path.getsize(self.session_file) > 0
            )
        except OSError:
            return False
