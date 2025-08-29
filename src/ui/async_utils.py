#!/usr/bin/env python3
"""Simple threading utilities for background tasks in the UI."""
from __future__ import annotations
import threading
from typing import Callable, Optional

# Type aliases
Action = Callable[[], None]
ErrorHandler = Callable[[Exception], None]


def run_background(task: Action,
                   before: Optional[Action] = None,
                   after: Optional[Action] = None,
                   on_error: Optional[ErrorHandler] = None,
                   name: str | None = None,
                   daemon: bool = True) -> None:
    """Execute a task in a background thread with optional hooks.

    Mirrors the previous pattern used in main_app but centralized.
    """
    def runner():
        try:
            if before:
                before()
            task()
        except Exception as e:  # noqa: BLE001
            if on_error:
                on_error(e)
            else:  # fallback debug print
                print(f"[run_background] Unhandled error in {name or 'task'}: {e}")
        finally:
            if after:
                after()
    t = threading.Thread(target=runner, daemon=daemon, name=name or 'bg-task')
    t.start()
