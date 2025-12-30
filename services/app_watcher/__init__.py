"""App watcher service - monitors active application for profile switching."""

from .watcher import ActiveWindowInfo, AppWatcher, GnomeWaylandBackend, WindowBackend, X11Backend

__all__ = [
    "ActiveWindowInfo",
    "AppWatcher",
    "WindowBackend",
    "X11Backend",
    "GnomeWaylandBackend",
]
