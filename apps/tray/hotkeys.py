"""Global hotkey listener for profile switching.

Listens for customizable hotkeys to switch profiles by position.
Supports both Wayland (via xdg-desktop-portal) and X11 (via pynput).
"""

import logging
from collections.abc import Callable

from crates.profile_schema import HotkeyBinding, SettingsManager

from .hotkey_backends import HotkeyBackend, PortalGlobalShortcuts, X11Hotkeys

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Global hotkey listener for profile switching.

    Automatically selects the best available backend:
    - Wayland: Uses xdg-desktop-portal GlobalShortcuts API
    - X11: Uses pynput keyboard listener

    Listens for user-configured hotkeys and calls the callback with profile index.
    """

    def __init__(
        self,
        on_profile_switch: Callable[[int], None],
        settings_manager: SettingsManager | None = None,
    ):
        """Initialize the hotkey listener.

        Args:
            on_profile_switch: Callback called with profile index (0-8) when hotkey pressed.
            settings_manager: Settings manager for hotkey configuration.
        """
        self.on_profile_switch = on_profile_switch
        self.settings_manager = settings_manager or SettingsManager()
        self._backend: HotkeyBackend | None = None
        self._init_backend()

    def _init_backend(self) -> None:
        """Select the best available backend for the current environment."""
        backends = [
            PortalGlobalShortcuts(self._on_shortcut_activated),
            X11Hotkeys(self._on_shortcut_activated),
        ]

        for backend in backends:
            if backend.is_available():
                self._backend = backend
                logger.info("Using hotkey backend: %s", backend.name)
                return

        logger.warning("No hotkey backend available")

    def _on_shortcut_activated(self, action_id: str) -> None:
        """Handle shortcut activation from backend.

        Args:
            action_id: The action ID (e.g., "profile_0", "profile_1")
        """
        try:
            # Extract profile index from action_id
            if action_id.startswith("profile_"):
                index = int(action_id.split("_")[1])
                self.on_profile_switch(index)
        except (ValueError, IndexError) as e:
            logger.error("Invalid action_id: %s (%s)", action_id, e)

    def _build_shortcuts(self) -> list[tuple[str, HotkeyBinding]]:
        """Build shortcuts list from settings.

        Returns:
            List of (action_id, binding) tuples
        """
        bindings = self.get_bindings()
        shortcuts = []
        for i, binding in enumerate(bindings):
            if binding.enabled and binding.key:
                action_id = f"profile_{i}"
                shortcuts.append((action_id, binding))
        return shortcuts

    def get_bindings(self) -> list[HotkeyBinding]:
        """Get current hotkey bindings from settings."""
        return self.settings_manager.settings.hotkeys.profile_hotkeys

    def reload_bindings(self) -> None:
        """Reload bindings from settings (call after settings change).

        This will re-register shortcuts with the backend.
        """
        # Force reload settings from disk
        self.settings_manager._settings = None
        self.settings_manager.load()

        # Re-register shortcuts if backend is running
        if self._backend:
            shortcuts = self._build_shortcuts()
            self._backend.register_shortcuts(shortcuts)
            logger.info("Reloaded %d hotkey bindings", len(shortcuts))

    def start(self) -> None:
        """Start listening for hotkeys."""
        if not self._backend:
            logger.warning("No backend available, hotkeys disabled")
            return

        # Register shortcuts and start backend
        shortcuts = self._build_shortcuts()
        self._backend.register_shortcuts(shortcuts)
        self._backend.start()
        logger.info("Hotkey listener started with %d shortcuts", len(shortcuts))

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        if self._backend:
            self._backend.stop()
            logger.info("Hotkey listener stopped")

    @property
    def backend_name(self) -> str | None:
        """Return the name of the active backend."""
        return self._backend.name if self._backend else None
