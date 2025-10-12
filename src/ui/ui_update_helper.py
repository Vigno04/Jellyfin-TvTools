#!/usr/bin/env python3
"""Helper utilities for safe UI updates in Flet."""
from __future__ import annotations
import functools
from typing import Callable, Any


def safe_ui_update(func: Callable) -> Callable:
    """
    Decorator to safely handle UI updates and prevent assertion errors.
    Wraps functions that update Flet controls to catch and log exceptions.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except AssertionError as e:
            print(f"[UI Update Error] AssertionError in {func.__name__}: {e}")
            # Silently ignore to prevent UI freeze
        except Exception as e:
            print(f"[UI Update Error] Exception in {func.__name__}: {e}")
            # Re-raise non-assertion errors for debugging
            raise
    return wrapper


def batch_update_controls(page, *controls):
    """
    Update multiple controls in a batch to reduce UI refresh cycles.
    
    Args:
        page: The Flet page instance
        *controls: Variable number of Flet controls to update
    """
    try:
        if controls:
            page.update(*controls)
    except AssertionError as e:
        print(f"[Batch Update Error] AssertionError: {e}")
        # Try updating page as fallback
        try:
            page.update()
        except:
            pass
    except Exception as e:
        print(f"[Batch Update Error] Exception: {e}")
        raise
