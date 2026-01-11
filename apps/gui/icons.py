"""Razer-styled icon system with lazy-loading and caching."""

from pathlib import Path

from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Resolve data directory relative to this file
_ICONS_DIR = Path(__file__).parent.parent.parent / "data" / "icons"


class RazerIcons:
    """SVG icon provider with caching and tinting support."""

    _cache: dict[str, QIcon] = {}
    _pixmap_cache: dict[str, QPixmap] = {}

    # Tab icons
    TAB_DEVICES = "devices"
    TAB_BINDINGS = "bindings"
    TAB_MACROS = "macros"
    TAB_APPS = "apps"
    TAB_LIGHTING = "lighting"
    TAB_DEVICE_VIEW = "device-view"
    TAB_ZONES = "zones"
    TAB_DPI = "dpi"
    TAB_BATTERY = "battery"
    TAB_DAEMON = "daemon"

    # Action icons
    ACTION_ADD = "plus"
    ACTION_DELETE = "trash"
    ACTION_EDIT = "edit"
    ACTION_REFRESH = "refresh"
    ACTION_APPLY = "check"
    ACTION_SAVE = "save"
    ACTION_IMPORT = "upload"
    ACTION_EXPORT = "download"
    ACTION_PLAY = "play"
    ACTION_STOP = "stop"
    ACTION_RECORD = "record"

    # Status icons
    STATUS_SUCCESS = "circle-check"
    STATUS_ERROR = "circle-x"
    STATUS_WARNING = "alert-triangle"
    STATUS_CHARGING = "bolt"
    STATUS_CONNECTED = "link"
    STATUS_DISCONNECTED = "link-off"

    # Device type icons
    DEVICE_MOUSE = "mouse"
    DEVICE_KEYBOARD = "keyboard"
    DEVICE_KEYPAD = "keypad"

    @classmethod
    def get(cls, name: str, size: int = 20, color: str | None = None) -> QIcon:
        """
        Get icon by name with optional size and color tinting.

        Args:
            name: Icon name (without .svg extension)
            size: Icon size in pixels (default 20)
            color: Optional hex color to tint the icon (e.g., "#2da05a")

        Returns:
            QIcon ready for use in widgets
        """
        cache_key = f"{name}_{size}_{color or 'default'}"
        if cache_key not in cls._cache:
            pixmap = cls._load_pixmap(name, size, color)
            cls._cache[cache_key] = QIcon(pixmap)
        return cls._cache[cache_key]

    @classmethod
    def get_pixmap(cls, name: str, size: int = 20, color: str | None = None) -> QPixmap:
        """
        Get pixmap by name for custom rendering.

        Args:
            name: Icon name (without .svg extension)
            size: Icon size in pixels (default 20)
            color: Optional hex color to tint the icon

        Returns:
            QPixmap for custom painting
        """
        cache_key = f"px_{name}_{size}_{color or 'default'}"
        if cache_key not in cls._pixmap_cache:
            cls._pixmap_cache[cache_key] = cls._load_pixmap(name, size, color)
        return cls._pixmap_cache[cache_key]

    @classmethod
    def _load_pixmap(cls, name: str, size: int, color: str | None) -> QPixmap:
        """Load and optionally tint an SVG icon."""
        # Try different subdirectories
        svg_path = cls._find_icon(name)

        if svg_path is None or not svg_path.exists():
            # Return empty pixmap if icon not found
            return cls._create_fallback_pixmap(name, size)

        # Render SVG at requested size
        renderer = QSvgRenderer(str(svg_path))
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        # Apply color tint if specified
        if color:
            pixmap = cls._tint_pixmap(pixmap, color)

        return pixmap

    @classmethod
    def _find_icon(cls, name: str) -> Path | None:
        """Find icon file in subdirectories."""
        # Check subdirectories
        subdirs = ["tabs", "actions", "status", "devices", ""]
        for subdir in subdirs:
            if subdir:
                path = _ICONS_DIR / subdir / f"{name}.svg"
            else:
                path = _ICONS_DIR / f"{name}.svg"
            if path.exists():
                return path
        return None

    @classmethod
    def _tint_pixmap(cls, pixmap: QPixmap, color: str) -> QPixmap:
        """Apply color tint to pixmap using composition."""
        tinted = QPixmap(pixmap.size())
        tinted.fill(QColor(0, 0, 0, 0))

        painter = QPainter(tinted)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), QColor(color))
        painter.end()

        return tinted

    @classmethod
    def _create_fallback_pixmap(cls, name: str, size: int) -> QPixmap:
        """Create a simple fallback icon when SVG is missing."""
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setPen(QColor("#666666"))
        painter.drawRect(2, 2, size - 4, size - 4)
        painter.end()

        return pixmap

    @classmethod
    def clear_cache(cls) -> None:
        """Clear all cached icons (useful for theme changes)."""
        cls._cache.clear()
        cls._pixmap_cache.clear()

    @classmethod
    def preload_common(cls) -> None:
        """Preload commonly used icons for faster initial display."""
        common_icons = [
            cls.TAB_DEVICES,
            cls.TAB_BINDINGS,
            cls.TAB_MACROS,
            cls.TAB_LIGHTING,
            cls.TAB_BATTERY,
            cls.TAB_DAEMON,
            cls.ACTION_ADD,
            cls.ACTION_DELETE,
            cls.ACTION_REFRESH,
        ]
        for icon_name in common_icons:
            cls.get(icon_name, 20)


# Convenience function for quick icon access
def icon(name: str, size: int = 20, color: str | None = None) -> QIcon:
    """Shorthand for RazerIcons.get()."""
    return RazerIcons.get(name, size, color)
