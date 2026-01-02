"""Tests for hotkey backends."""

import os
from unittest.mock import MagicMock, patch

import pytest

from apps.tray.hotkey_backends import (
    HotkeyBackend,
    PortalGlobalShortcuts,
    X11Hotkeys,
    to_portal_format,
)
from apps.tray.hotkeys import HotkeyListener
from crates.profile_schema import HotkeyBinding, SettingsManager


class TestToPortalFormat:
    """Tests for shortcut format conversion."""

    def test_ctrl_shift_number(self):
        """Test Ctrl+Shift+1 conversion."""
        binding = HotkeyBinding(modifiers=["ctrl", "shift"], key="1")
        assert to_portal_format(binding) == "<Primary><Shift>1"

    def test_ctrl_alt_letter(self):
        """Test Ctrl+Alt+A conversion."""
        binding = HotkeyBinding(modifiers=["ctrl", "alt"], key="a")
        assert to_portal_format(binding) == "<Primary><Alt>a"

    def test_alt_function_key(self):
        """Test Alt+F1 conversion."""
        binding = HotkeyBinding(modifiers=["alt"], key="f1")
        assert to_portal_format(binding) == "<Alt>F1"

    def test_shift_only(self):
        """Test Shift+X conversion."""
        binding = HotkeyBinding(modifiers=["shift"], key="x")
        assert to_portal_format(binding) == "<Shift>x"

    def test_all_modifiers(self):
        """Test Ctrl+Alt+Shift+Z conversion."""
        binding = HotkeyBinding(modifiers=["ctrl", "alt", "shift"], key="z")
        assert to_portal_format(binding) == "<Primary><Alt><Shift>z"

    def test_function_key_only(self):
        """Test F12 with no modifiers."""
        binding = HotkeyBinding(modifiers=[], key="f12")
        assert to_portal_format(binding) == "F12"


class TestPortalGlobalShortcuts:
    """Tests for Portal backend."""

    def test_not_available_on_x11(self):
        """Portal should not be available on X11."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            backend = PortalGlobalShortcuts(lambda x: None)
            assert not backend.is_available()

    def test_not_available_without_wayland(self):
        """Portal should not be available without Wayland."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": ""}):
            backend = PortalGlobalShortcuts(lambda x: None)
            assert not backend.is_available()

    def test_checks_wayland_session(self):
        """Portal checks for Wayland session type."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            with patch("pydbus.SessionBus") as mock_bus:
                # Simulate portal not available
                mock_bus.side_effect = Exception("No portal")
                backend = PortalGlobalShortcuts(lambda x: None)
                assert not backend.is_available()

    def test_name_property(self):
        """Backend name should be class name."""
        backend = PortalGlobalShortcuts(lambda x: None)
        assert backend.name == "PortalGlobalShortcuts"

    def test_register_shortcuts(self):
        """Register shortcuts should store them."""
        backend = PortalGlobalShortcuts(lambda x: None)
        shortcuts = [
            ("profile_0", HotkeyBinding(modifiers=["ctrl"], key="1")),
            ("profile_1", HotkeyBinding(modifiers=["ctrl"], key="2")),
        ]
        assert backend.register_shortcuts(shortcuts)
        assert backend._shortcuts == shortcuts


class TestX11Hotkeys:
    """Tests for X11 backend."""

    def test_available_on_x11(self):
        """X11 backend should be available on X11."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            backend = X11Hotkeys(lambda x: None)
            assert backend.is_available()

    def test_available_when_unset(self):
        """X11 backend should be available when session type not set."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": ""}, clear=False):
            # Remove the key entirely for this test
            env = os.environ.copy()
            if "XDG_SESSION_TYPE" in env:
                del env["XDG_SESSION_TYPE"]
            with patch.dict(os.environ, env, clear=True):
                backend = X11Hotkeys(lambda x: None)
                # Will check pynput import
                assert backend.is_available()

    def test_not_available_on_wayland(self):
        """X11 backend should not be available on Wayland."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            backend = X11Hotkeys(lambda x: None)
            assert not backend.is_available()

    def test_name_property(self):
        """Backend name should be class name."""
        backend = X11Hotkeys(lambda x: None)
        assert backend.name == "X11Hotkeys"

    def test_register_shortcuts(self):
        """Register shortcuts should store them."""
        backend = X11Hotkeys(lambda x: None)
        shortcuts = [
            ("profile_0", HotkeyBinding(modifiers=["ctrl"], key="1")),
        ]
        assert backend.register_shortcuts(shortcuts)
        assert backend._shortcuts == shortcuts

    def test_check_binding_matching(self):
        """Check binding should match pressed keys."""
        backend = X11Hotkeys(lambda x: None)
        binding = HotkeyBinding(modifiers=["ctrl", "shift"], key="1", enabled=True)

        # No keys pressed
        assert not backend._check_binding(binding)

        # Some modifiers pressed
        backend._current_keys = {"ctrl"}
        assert not backend._check_binding(binding)

        # All modifiers but not key
        backend._current_keys = {"ctrl", "shift"}
        assert not backend._check_binding(binding)

        # All pressed
        backend._current_keys = {"ctrl", "shift", "1"}
        assert backend._check_binding(binding)

    def test_check_binding_disabled(self):
        """Disabled bindings should not match."""
        backend = X11Hotkeys(lambda x: None)
        binding = HotkeyBinding(modifiers=["ctrl"], key="1", enabled=False)
        backend._current_keys = {"ctrl", "1"}
        assert not backend._check_binding(binding)

    def test_check_binding_empty_key(self):
        """Empty key bindings should not match."""
        backend = X11Hotkeys(lambda x: None)
        binding = HotkeyBinding(modifiers=["ctrl"], key="", enabled=True)
        backend._current_keys = {"ctrl"}
        assert not backend._check_binding(binding)


class TestHotkeyListener:
    """Tests for HotkeyListener."""

    def test_selects_x11_on_x11_session(self):
        """Should select X11 backend on X11 session."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            callback = MagicMock()
            listener = HotkeyListener(callback)
            assert listener.backend_name == "X11Hotkeys"

    def test_no_backend_when_none_available(self):
        """Should have no backend when none available."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}):
            with patch(
                "apps.tray.hotkey_backends.PortalGlobalShortcuts.is_available",
                return_value=False,
            ):
                with patch(
                    "apps.tray.hotkey_backends.X11Hotkeys.is_available",
                    return_value=False,
                ):
                    callback = MagicMock()
                    listener = HotkeyListener(callback)
                    assert listener.backend_name is None

    def test_build_shortcuts(self):
        """Should build shortcuts from settings."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            callback = MagicMock()
            settings = SettingsManager()
            listener = HotkeyListener(callback, settings)

            shortcuts = listener._build_shortcuts()
            # Default settings have 9 enabled shortcuts
            assert len(shortcuts) == 9
            assert shortcuts[0][0] == "profile_0"
            assert shortcuts[0][1].key == "1"

    def test_on_shortcut_activated(self):
        """Should call callback with profile index."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            callback = MagicMock()
            listener = HotkeyListener(callback)

            listener._on_shortcut_activated("profile_3")
            callback.assert_called_once_with(3)

    def test_on_shortcut_activated_invalid(self):
        """Should handle invalid action IDs gracefully."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            callback = MagicMock()
            listener = HotkeyListener(callback)

            # Should not crash
            listener._on_shortcut_activated("invalid")
            listener._on_shortcut_activated("profile_")
            listener._on_shortcut_activated("profile_abc")
            callback.assert_not_called()

    def test_start_registers_shortcuts(self):
        """Start should register shortcuts with backend."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            callback = MagicMock()
            listener = HotkeyListener(callback)

            with patch.object(
                listener._backend, "register_shortcuts"
            ) as mock_register:
                with patch.object(listener._backend, "start"):
                    listener.start()
                    mock_register.assert_called_once()

    def test_stop_stops_backend(self):
        """Stop should stop the backend."""
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}):
            callback = MagicMock()
            listener = HotkeyListener(callback)

            with patch.object(listener._backend, "stop") as mock_stop:
                listener.stop()
                mock_stop.assert_called_once()
