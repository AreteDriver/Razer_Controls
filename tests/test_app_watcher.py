"""Tests for the app watcher service."""

from unittest.mock import MagicMock, patch

import pytest

from services.app_watcher import ActiveWindowInfo, AppWatcher, GnomeWaylandBackend, X11Backend


class TestActiveWindowInfo:
    """Tests for ActiveWindowInfo dataclass."""

    def test_creation(self):
        """Test creating window info."""
        info = ActiveWindowInfo(pid=1234, process_name="firefox")
        assert info.pid == 1234
        assert info.process_name == "firefox"
        assert info.window_class is None
        assert info.window_title is None

    def test_full_creation(self):
        """Test creating window info with all fields."""
        info = ActiveWindowInfo(
            pid=1234,
            process_name="firefox",
            window_class="Navigator",
            window_title="Mozilla Firefox",
        )
        assert info.pid == 1234
        assert info.process_name == "firefox"
        assert info.window_class == "Navigator"
        assert info.window_title == "Mozilla Firefox"

    def test_repr(self):
        """Test string representation."""
        info = ActiveWindowInfo(pid=1234, process_name="firefox", window_class="Navigator")
        repr_str = repr(info)
        assert "1234" in repr_str
        assert "firefox" in repr_str


class TestPatternMatching:
    """Tests for pattern matching in AppWatcher."""

    @pytest.fixture
    def watcher(self):
        """Create a watcher instance for testing."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = None
            return watcher

    def test_exact_match(self, watcher):
        """Test exact string matching."""
        assert watcher._matches_pattern("firefox", "firefox") is True
        assert watcher._matches_pattern("Firefox", "firefox") is True  # Case insensitive
        assert watcher._matches_pattern("chrome", "firefox") is False

    def test_wildcard_match(self, watcher):
        """Test wildcard pattern matching."""
        assert watcher._matches_pattern("firefox", "fire*") is True
        assert watcher._matches_pattern("firefox", "*fox") is True
        assert watcher._matches_pattern("game.exe", "*.exe") is True
        assert watcher._matches_pattern("game.bin", "*.exe") is False

    def test_substring_match(self, watcher):
        """Test substring matching."""
        assert watcher._matches_pattern("steam_app_12345", "steam") is True
        assert watcher._matches_pattern("com.google.chrome", "chrome") is True

    def test_case_insensitive(self, watcher):
        """Test case insensitive matching."""
        assert watcher._matches_pattern("FIREFOX", "firefox") is True
        assert watcher._matches_pattern("Firefox", "FIREFOX") is True
        assert watcher._matches_pattern("steam_app", "Steam") is True


class TestX11Backend:
    """Tests for X11 backend."""

    def test_is_available_with_xdotool(self):
        """Test availability check when xdotool exists."""
        backend = X11Backend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert backend.is_available() is True

    def test_is_available_without_xdotool(self):
        """Test availability check when xdotool doesn't exist."""
        backend = X11Backend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert backend.is_available() is False

    def test_get_active_window_success(self):
        """Test getting active window info."""
        backend = X11Backend()

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            if cmd[1] == "getactivewindow":
                result.returncode = 0
                result.stdout = "12345678"
            elif cmd[1] == "getwindowpid":
                result.returncode = 0
                result.stdout = "1234"
            elif cmd[1] == "getwindowclassname":
                result.returncode = 0
                result.stdout = "Navigator"
            elif cmd[1] == "getwindowname":
                result.returncode = 0
                result.stdout = "Firefox"
            else:
                result.returncode = 1
            return result

        with patch("subprocess.run", side_effect=mock_run):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.read_text", return_value="firefox\n"):
                    info = backend.get_active_window()

        assert info is not None
        assert info.pid == 1234
        assert info.process_name == "firefox"
        assert info.window_class == "Navigator"
        assert info.window_title == "Firefox"

    def test_get_active_window_no_window(self):
        """Test when no window is active."""
        backend = X11Backend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            info = backend.get_active_window()
            assert info is None


class TestGnomeWaylandBackend:
    """Tests for GNOME Wayland backend."""

    def test_is_available_on_gnome_wayland(self):
        """Test availability on GNOME Wayland."""
        backend = GnomeWaylandBackend()
        env = {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "GNOME"}
        with patch.dict("os.environ", env):
            assert backend.is_available() is True

    def test_is_available_on_x11(self):
        """Test availability on X11."""
        backend = GnomeWaylandBackend()
        with patch.dict("os.environ", {"XDG_SESSION_TYPE": "x11", "XDG_CURRENT_DESKTOP": "GNOME"}):
            assert backend.is_available() is False

    def test_is_available_on_kde(self):
        """Test availability on KDE."""
        backend = GnomeWaylandBackend()
        env = {"XDG_SESSION_TYPE": "wayland", "XDG_CURRENT_DESKTOP": "KDE"}
        with patch.dict("os.environ", env):
            assert backend.is_available() is False


class TestAppWatcher:
    """Tests for the main AppWatcher class."""

    def test_start_without_backend(self):
        """Test starting watcher without a backend."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = None
            assert watcher.start() is False

    def test_is_running(self):
        """Test is_running property."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = None
            assert watcher.is_running is False

    def test_backend_name_none(self):
        """Test backend_name when no backend."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = None
            assert watcher.backend_name is None

    def test_backend_name_x11(self):
        """Test backend_name with X11 backend."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = X11Backend()
            assert watcher.backend_name == "X11Backend"

    def test_stop_when_not_running(self):
        """Test stopping when not running."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = None
            watcher.stop()  # Should not raise
            assert watcher.is_running is False


class TestWindowBackendBase:
    """Tests for WindowBackend base class."""

    def test_get_active_window_not_implemented(self):
        """Test base class raises NotImplementedError (line 40)."""
        from services.app_watcher.watcher import WindowBackend

        backend = WindowBackend()
        with pytest.raises(NotImplementedError):
            backend.get_active_window()

    def test_is_available_not_implemented(self):
        """Test base class raises NotImplementedError (line 44)."""
        from services.app_watcher.watcher import WindowBackend

        backend = WindowBackend()
        with pytest.raises(NotImplementedError):
            backend.is_available()


class TestX11BackendEdgeCases:
    """Additional X11Backend edge case tests."""

    def test_is_available_exception(self):
        """Test is_available returns False on exception (lines 55-56)."""
        backend = X11Backend()
        with patch("subprocess.run", side_effect=Exception("Command failed")):
            assert backend.is_available() is False

    def test_get_active_window_empty_window_id(self):
        """Test get_active_window with empty window ID (line 70)."""
        backend = X11Backend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            info = backend.get_active_window()
            assert info is None

    def test_get_active_window_invalid_pid(self):
        """Test get_active_window with invalid PID (lines 80-81)."""
        backend = X11Backend()

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            if cmd[1] == "getactivewindow":
                result.returncode = 0
                result.stdout = "12345"
            elif cmd[1] == "getwindowpid":
                result.returncode = 0
                result.stdout = "not_a_number"  # Invalid PID
            elif cmd[1] == "getwindowclassname":
                result.returncode = 0
                result.stdout = "Class"
            elif cmd[1] == "getwindowname":
                result.returncode = 0
                result.stdout = "Title"
            else:
                result.returncode = 1
            return result

        with patch("subprocess.run", side_effect=mock_run):
            info = backend.get_active_window()
            assert info is not None
            assert info.pid is None  # PID should be None due to ValueError

    def test_get_active_window_proc_comm_exception(self):
        """Test get_active_window when /proc/comm raises exception (lines 90-91)."""
        backend = X11Backend()

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            if cmd[1] == "getactivewindow":
                result.returncode = 0
                result.stdout = "12345"
            elif cmd[1] == "getwindowpid":
                result.returncode = 0
                result.stdout = "1234"
            else:
                result.returncode = 0
                result.stdout = "data"
            return result

        with patch("subprocess.run", side_effect=mock_run):
            with patch("pathlib.Path.exists", side_effect=PermissionError("Access denied")):
                info = backend.get_active_window()
                assert info is not None
                # process_name should try exe fallback

    def test_get_active_window_exe_fallback(self):
        """Test get_active_window uses exe symlink fallback (lines 95-99)."""
        backend = X11Backend()

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            if cmd[1] == "getactivewindow":
                result.returncode = 0
                result.stdout = "12345"
            elif cmd[1] == "getwindowpid":
                result.returncode = 0
                result.stdout = "1234"
            else:
                result.returncode = 0
                result.stdout = "data"
            return result

        from pathlib import Path

        mock_path = MagicMock(spec=Path)

        with patch("subprocess.run", side_effect=mock_run):
            with patch("pathlib.Path.exists", return_value=False):  # comm doesn't exist
                with patch("pathlib.Path.resolve") as mock_resolve:
                    mock_resolve.return_value = Path("/usr/bin/firefox")
                    info = backend.get_active_window()
                    assert info is not None

    def test_get_active_window_exe_exception(self):
        """Test get_active_window handles exe symlink exception (lines 95-99)."""
        backend = X11Backend()

        def mock_run(cmd, **kwargs):
            result = MagicMock()
            if cmd[1] == "getactivewindow":
                result.returncode = 0
                result.stdout = "12345"
            elif cmd[1] == "getwindowpid":
                result.returncode = 0
                result.stdout = "1234"
            else:
                result.returncode = 0
                result.stdout = "data"
            return result

        with patch("subprocess.run", side_effect=mock_run):
            with patch("pathlib.Path.exists", return_value=False):  # comm doesn't exist
                with patch("pathlib.Path.resolve", side_effect=OSError("No symlink")):
                    info = backend.get_active_window()
                    assert info is not None

    def test_get_active_window_timeout(self):
        """Test get_active_window handles timeout (lines 127-128)."""
        import subprocess

        backend = X11Backend()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 2)):
            info = backend.get_active_window()
            assert info is None

    def test_get_active_window_exception(self):
        """Test get_active_window handles general exception (lines 129-130)."""
        backend = X11Backend()
        with patch("subprocess.run", side_effect=Exception("Unknown error")):
            info = backend.get_active_window()
            assert info is None


class TestGnomeWaylandBackendGetWindow:
    """Tests for GnomeWaylandBackend.get_active_window."""

    def test_get_active_window_success(self):
        """Test successful window info retrieval (lines 146-200)."""
        backend = GnomeWaylandBackend()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="(true, '1234')")
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.read_text", return_value="firefox\n"):
                    info = backend.get_active_window()

        assert info is not None
        assert info.pid == 1234
        assert info.process_name == "firefox"

    def test_get_active_window_failed_command(self):
        """Test get_active_window with failed gdbus command (lines 172-173)."""
        backend = GnomeWaylandBackend()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            info = backend.get_active_window()

        assert info is None

    def test_get_active_window_false_result(self):
        """Test get_active_window with false result (lines 177-178)."""
        backend = GnomeWaylandBackend()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="(false, '')")
            info = backend.get_active_window()

        assert info is None

    def test_get_active_window_no_pid_match(self):
        """Test get_active_window with no PID in result (lines 184-185)."""
        backend = GnomeWaylandBackend()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="(true, 'no_number')")
            info = backend.get_active_window()

        assert info is None

    def test_get_active_window_zero_pid(self):
        """Test get_active_window with zero PID (lines 188-189)."""
        backend = GnomeWaylandBackend()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="(true, '0')")
            info = backend.get_active_window()

        assert info is None

    def test_get_active_window_proc_exception(self):
        """Test get_active_window handles /proc exception (lines 197-198)."""
        backend = GnomeWaylandBackend()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="(true, '1234')")
            with patch("pathlib.Path.exists", side_effect=OSError("No access")):
                info = backend.get_active_window()

        assert info is not None
        assert info.pid == 1234
        assert info.process_name is None

    def test_get_active_window_exception(self):
        """Test get_active_window handles general exception (lines 202-203)."""
        backend = GnomeWaylandBackend()

        with patch("subprocess.run", side_effect=Exception("Unknown")):
            info = backend.get_active_window()

        assert info is None


class TestAppWatcherInitBackend:
    """Tests for AppWatcher._init_backend."""

    def test_init_backend_selects_gnome_wayland(self):
        """Test _init_backend selects GNOME Wayland when available (lines 235-244)."""
        with patch.object(GnomeWaylandBackend, "is_available", return_value=True):
            watcher = AppWatcher()
            assert isinstance(watcher._backend, GnomeWaylandBackend)

    def test_init_backend_selects_x11_fallback(self):
        """Test _init_backend falls back to X11 (lines 235-244)."""
        with patch.object(GnomeWaylandBackend, "is_available", return_value=False):
            with patch.object(X11Backend, "is_available", return_value=True):
                watcher = AppWatcher()
                assert isinstance(watcher._backend, X11Backend)

    def test_init_backend_no_backend_available(self):
        """Test _init_backend with no backends (line 246)."""
        with patch.object(GnomeWaylandBackend, "is_available", return_value=False):
            with patch.object(X11Backend, "is_available", return_value=False):
                watcher = AppWatcher()
                assert watcher._backend is None


class TestAppWatcherStartStop:
    """Tests for AppWatcher start/stop."""

    def test_start_already_running(self):
        """Test start when already running (lines 254-255)."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = MagicMock()
            watcher._running = True
            result = watcher.start()
            assert result is True  # Returns True, doesn't start new thread

    def test_start_creates_thread(self):
        """Test start creates daemon thread (lines 257-261)."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = MagicMock()
            watcher._running = False

            with patch("threading.Thread") as mock_thread_class:
                mock_thread = MagicMock()
                mock_thread_class.return_value = mock_thread

                result = watcher.start()

                assert result is True
                mock_thread_class.assert_called_once()
                mock_thread.start.assert_called_once()
                watcher._running = False  # Clean up

    def test_stop_joins_thread(self):
        """Test stop joins the thread (lines 267-268)."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = MagicMock()
            watcher._running = True

            mock_thread = MagicMock()
            watcher._thread = mock_thread

            watcher.stop()

            mock_thread.join.assert_called_once_with(timeout=2)
            assert watcher._thread is None


class TestAppWatcherWatchLoop:
    """Tests for AppWatcher._watch_loop."""

    def test_watch_loop_checks_window(self):
        """Test watch loop calls _check_active_window (lines 273-279)."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = MagicMock()
            watcher.poll_interval = 0.01

            call_count = [0]

            def mock_check():
                call_count[0] += 1
                if call_count[0] >= 2:
                    watcher._running = False

            watcher._check_active_window = mock_check
            watcher._running = True
            watcher._watch_loop()

            assert call_count[0] >= 2

    def test_watch_loop_handles_exception(self):
        """Test watch loop handles exceptions (lines 276-277)."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = MagicMock()
            watcher.poll_interval = 0.01

            call_count = [0]

            def mock_check():
                call_count[0] += 1
                if call_count[0] == 1:
                    raise Exception("Test error")
                else:
                    watcher._running = False

            watcher._check_active_window = mock_check
            watcher._running = True
            watcher._watch_loop()  # Should not raise

            assert call_count[0] >= 2


class TestAppWatcherCheckActiveWindow:
    """Tests for AppWatcher._check_active_window."""

    def test_check_active_window_no_backend(self):
        """Test _check_active_window with no backend (lines 283-284)."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = None
            watcher._check_active_window()  # Should return early

    def test_check_active_window_no_window_info(self):
        """Test _check_active_window when backend returns None (lines 287-288)."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = MagicMock()
            watcher._backend.get_active_window.return_value = None
            watcher._check_active_window()  # Should return early

    def test_check_active_window_same_window(self):
        """Test _check_active_window when window unchanged (lines 291-296)."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = MagicMock()

            window_info = ActiveWindowInfo(pid=1234, process_name="firefox")
            watcher._backend.get_active_window.return_value = window_info
            watcher._last_window_info = window_info

            watcher._check_active_window()  # Should return early (same window)

    def test_check_active_window_profile_switch(self):
        """Test _check_active_window triggers profile switch (lines 298-311)."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = MagicMock()

            window_info = ActiveWindowInfo(pid=1234, process_name="firefox")
            watcher._backend.get_active_window.return_value = window_info

            from crates.profile_schema import Layer, Profile

            mock_profile = Profile(
                id="gaming", name="Gaming", layers=[Layer(id="base", name="Base", bindings=[])]
            )
            watcher._find_matching_profile = MagicMock(return_value=mock_profile)

            callback_called = []
            watcher.on_profile_change = lambda p: callback_called.append(p)

            watcher._check_active_window()

            assert len(callback_called) == 1
            assert callback_called[0] == mock_profile
            assert watcher._current_profile_id == "gaming"

    def test_check_active_window_same_profile(self):
        """Test _check_active_window doesn't switch to same profile (line 303)."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()
            watcher._backend = MagicMock()
            watcher._current_profile_id = "gaming"

            window_info = ActiveWindowInfo(pid=1234, process_name="firefox")
            watcher._backend.get_active_window.return_value = window_info

            from crates.profile_schema import Layer, Profile

            mock_profile = Profile(
                id="gaming", name="Gaming", layers=[Layer(id="base", name="Base", bindings=[])]
            )
            watcher._find_matching_profile = MagicMock(return_value=mock_profile)

            callback_called = []
            watcher.on_profile_change = lambda p: callback_called.append(p)

            watcher._check_active_window()

            assert len(callback_called) == 0  # Shouldn't switch to same profile


class TestAppWatcherFindMatchingProfile:
    """Tests for AppWatcher._find_matching_profile."""

    def test_find_matching_profile_process_match(self):
        """Test finding profile by process name (lines 328-331)."""
        from crates.profile_schema import Layer, Profile

        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()

            gaming_profile = Profile(
                id="gaming",
                name="Gaming",
                layers=[Layer(id="base", name="Base", bindings=[])],
                match_process_names=["firefox", "chrome"],
            )

            watcher.profile_loader = MagicMock()
            watcher.profile_loader.list_profiles.return_value = ["gaming"]
            watcher.profile_loader.load_profile.return_value = gaming_profile

            window_info = ActiveWindowInfo(pid=1234, process_name="firefox")
            result = watcher._find_matching_profile(window_info)

            assert result == gaming_profile

    def test_find_matching_profile_window_class_match(self):
        """Test finding profile by window class (lines 334-336)."""
        from crates.profile_schema import Layer, Profile

        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()

            gaming_profile = Profile(
                id="gaming",
                name="Gaming",
                layers=[Layer(id="base", name="Base", bindings=[])],
                match_process_names=["Navigator"],  # Window class
            )

            watcher.profile_loader = MagicMock()
            watcher.profile_loader.list_profiles.return_value = ["gaming"]
            watcher.profile_loader.load_profile.return_value = gaming_profile

            window_info = ActiveWindowInfo(
                pid=1234, process_name="unknown", window_class="Navigator"
            )
            result = watcher._find_matching_profile(window_info)

            assert result == gaming_profile

    def test_find_matching_profile_default_fallback(self):
        """Test falling back to default profile (lines 324-325, 339)."""
        from crates.profile_schema import Layer, Profile

        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()

            default_profile = Profile(
                id="default",
                name="Default",
                layers=[Layer(id="base", name="Base", bindings=[])],
                is_default=True,
            )

            watcher.profile_loader = MagicMock()
            watcher.profile_loader.list_profiles.return_value = ["default"]
            watcher.profile_loader.load_profile.return_value = default_profile

            window_info = ActiveWindowInfo(pid=1234, process_name="unknown_app")
            result = watcher._find_matching_profile(window_info)

            assert result == default_profile

    def test_find_matching_profile_no_profile_loaded(self):
        """Test when profile loading fails (lines 320-321)."""
        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()

            watcher.profile_loader = MagicMock()
            watcher.profile_loader.list_profiles.return_value = ["bad_profile"]
            watcher.profile_loader.load_profile.return_value = None  # Failed to load

            window_info = ActiveWindowInfo(pid=1234, process_name="firefox")
            result = watcher._find_matching_profile(window_info)

            assert result is None

    def test_find_matching_profile_no_process_name(self):
        """Test with no process name in window info (line 328)."""
        from crates.profile_schema import Layer, Profile

        with patch.object(AppWatcher, "_init_backend"):
            watcher = AppWatcher()

            gaming_profile = Profile(
                id="gaming",
                name="Gaming",
                layers=[Layer(id="base", name="Base", bindings=[])],
                match_process_names=["firefox"],
            )

            watcher.profile_loader = MagicMock()
            watcher.profile_loader.list_profiles.return_value = ["gaming"]
            watcher.profile_loader.load_profile.return_value = gaming_profile

            window_info = ActiveWindowInfo(pid=1234, process_name=None)
            result = watcher._find_matching_profile(window_info)

            assert result is None
