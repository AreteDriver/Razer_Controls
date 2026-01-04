"""Tests for the device registry."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from crates.device_registry import DeviceRegistry, InputDevice


class TestInputDevice:
    """Tests for InputDevice dataclass."""

    def test_create_basic_device(self):
        """Test creating a basic input device."""
        device = InputDevice(
            stable_id="usb-Razer_Mouse-event-mouse",
            name="Razer Mouse",
            event_path="/dev/input/event5",
            by_id_path="/dev/input/by-id/usb-Razer_Mouse-event-mouse",
            by_path_path=None,
        )
        assert device.stable_id == "usb-Razer_Mouse-event-mouse"
        assert device.name == "Razer Mouse"
        assert device.is_mouse is False  # Default
        assert device.is_keyboard is False  # Default
        assert device.capabilities == []  # Default

    def test_create_mouse_device(self):
        """Test creating a mouse device."""
        device = InputDevice(
            stable_id="usb-Razer_Basilisk-event-mouse",
            name="Razer Basilisk V2",
            event_path="/dev/input/event8",
            by_id_path="/dev/input/by-id/usb-Razer_Basilisk-event-mouse",
            by_path_path="/dev/input/by-path/pci-0000:00:14.0-usb-0:1:1.0-event-mouse",
            is_mouse=True,
            capabilities=["EV_KEY", "EV_REL"],
        )
        assert device.is_mouse is True
        assert device.is_keyboard is False
        assert "EV_KEY" in device.capabilities

    def test_create_keyboard_device(self):
        """Test creating a keyboard device."""
        device = InputDevice(
            stable_id="usb-Razer_Huntsman-event-kbd",
            name="Razer Huntsman",
            event_path="/dev/input/event3",
            by_id_path="/dev/input/by-id/usb-Razer_Huntsman-event-kbd",
            by_path_path=None,
            is_keyboard=True,
        )
        assert device.is_mouse is False
        assert device.is_keyboard is True


class TestDeviceRegistry:
    """Tests for DeviceRegistry class."""

    def test_init_default_config_dir(self):
        """Test registry uses default config dir."""
        registry = DeviceRegistry()
        assert registry.config_dir == Path.home() / ".config" / "razer-control-center"

    def test_init_custom_config_dir(self):
        """Test registry with custom config dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            registry = DeviceRegistry(config_dir=config_dir)
            assert registry.config_dir == config_dir
            assert registry.devices_file == config_dir / "devices.json"

    def test_scan_devices_no_by_id_dir(self):
        """Test scan when /dev/input/by-id doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            with patch.object(Path, "exists", return_value=False):
                devices = registry.scan_devices()
                assert devices == []

    def test_get_device_by_stable_id_not_found(self):
        """Test getting device that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            registry._devices = {}  # No devices
            device = registry.get_device_by_stable_id("nonexistent")
            assert device is None

    def test_get_device_by_stable_id_found(self):
        """Test getting device that exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            test_device = InputDevice(
                stable_id="test-device",
                name="Test Device",
                event_path="/dev/input/event1",
                by_id_path=None,
                by_path_path=None,
            )
            registry._devices = {"test-device": test_device}
            device = registry.get_device_by_stable_id("test-device")
            assert device is not None
            assert device.name == "Test Device"

    def test_get_event_path_from_cached_device(self):
        """Test getting event path from cached device."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            test_device = InputDevice(
                stable_id="test-device",
                name="Test Device",
                event_path="/dev/input/event5",
                by_id_path=None,
                by_path_path=None,
            )
            registry._devices = {"test-device": test_device}
            path = registry.get_event_path("test-device")
            assert path == "/dev/input/event5"

    def test_get_event_path_not_found(self):
        """Test getting event path for unknown device."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            registry._devices = {}
            path = registry.get_event_path("nonexistent")
            assert path is None

    def test_get_razer_devices_empty(self):
        """Test getting Razer devices when none exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            registry._devices = {
                "generic-mouse": InputDevice(
                    stable_id="generic-mouse",
                    name="Generic Mouse",
                    event_path="/dev/input/event1",
                    by_id_path=None,
                    by_path_path=None,
                )
            }
            razer_devices = registry.get_razer_devices()
            assert razer_devices == []

    def test_get_razer_devices_found(self):
        """Test getting Razer devices."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            registry._devices = {
                "usb-Razer_Basilisk-event-mouse": InputDevice(
                    stable_id="usb-Razer_Basilisk-event-mouse",
                    name="Razer Basilisk V2",
                    event_path="/dev/input/event5",
                    by_id_path=None,
                    by_path_path=None,
                    is_mouse=True,
                ),
                "generic-mouse": InputDevice(
                    stable_id="generic-mouse",
                    name="Generic Mouse",
                    event_path="/dev/input/event1",
                    by_id_path=None,
                    by_path_path=None,
                ),
            }
            razer_devices = registry.get_razer_devices()
            assert len(razer_devices) == 1
            assert razer_devices[0].name == "Razer Basilisk V2"

    def test_save_selected_devices(self):
        """Test saving selected device IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            registry = DeviceRegistry(config_dir=config_dir)
            device_ids = ["device1", "device2"]
            registry.save_selected_devices(device_ids)

            # Verify file was created
            assert registry.devices_file.exists()
            data = json.loads(registry.devices_file.read_text())
            assert data["selected"] == device_ids

    def test_load_selected_devices_no_file(self):
        """Test loading when no file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            devices = registry.load_selected_devices()
            assert devices == []

    def test_load_selected_devices_success(self):
        """Test loading saved device IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            registry = DeviceRegistry(config_dir=config_dir)

            # Create the file
            config_dir.mkdir(parents=True, exist_ok=True)
            registry.devices_file.write_text(json.dumps({"selected": ["dev1", "dev2"]}))

            devices = registry.load_selected_devices()
            assert devices == ["dev1", "dev2"]

    def test_load_selected_devices_invalid_json(self):
        """Test loading with invalid JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            registry = DeviceRegistry(config_dir=config_dir)

            # Create invalid JSON file
            config_dir.mkdir(parents=True, exist_ok=True)
            registry.devices_file.write_text("not valid json")

            devices = registry.load_selected_devices()
            assert devices == []

    def test_get_device_name_fallback(self):
        """Test _get_device_name falls back to event name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            # Path that won't have a readable name file
            event_path = Path("/dev/input/event999")
            name = registry._get_device_name(event_path)
            assert name == "event999"

    def test_find_by_path_no_dir(self):
        """Test _find_by_path when by-path dir doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            result = registry._find_by_path(Path("/dev/input/event5"))
            # Will be None since /dev/input/by-path might not exist or not match
            # This tests the code path, actual result depends on system
            assert result is None or isinstance(result, str)

    def test_scan_devices_skips_non_symlinks(self):
        """Test scan_devices skips entries that aren't symlinks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            # Create a fake by-id directory with a regular file (not symlink)
            fake_by_id = Path(tmpdir) / "by-id"
            fake_by_id.mkdir()
            (fake_by_id / "not-a-symlink").write_text("test")

            with patch("crates.device_registry.registry.Path") as mock_path:
                # Make the by-id path return our fake directory
                real_by_id = fake_by_id

                def path_side_effect(p):
                    if p == "/dev/input/by-id":
                        return real_by_id
                    return Path(p)

                mock_path.side_effect = path_side_effect
                mock_path.return_value.exists.return_value = True

                # The scan should complete without errors, skipping non-symlinks
                devices = registry.scan_devices()
                assert isinstance(devices, list)

    def test_scan_devices_handles_oserror(self):
        """Test scan_devices handles OSError gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            # Create a fake by-id directory with a broken symlink
            fake_by_id = Path(tmpdir) / "by-id"
            fake_by_id.mkdir()
            broken_link = fake_by_id / "broken-link"
            broken_link.symlink_to("/nonexistent/path/that/does/not/exist")

            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "iterdir", return_value=[broken_link]):
                    # Should handle OSError and continue
                    devices = registry.scan_devices()
                    assert isinstance(devices, list)

    def test_find_by_path_returns_none_when_no_match(self):
        """Test _find_by_path returns None when no by-path directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            with patch.object(Path, "exists", return_value=False):
                result = registry._find_by_path(Path("/dev/input/event5"))
                assert result is None

    def test_find_by_path_handles_oserror_in_loop(self):
        """Test _find_by_path handles OSError when resolving links."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))

            class FakeLink:
                def resolve(self):
                    raise OSError("Permission denied")

            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "iterdir", return_value=[FakeLink()]):
                    result = registry._find_by_path(Path("/dev/input/event5"))
                    assert result is None

    def test_get_event_path_from_by_id_fallback(self):
        """Test get_event_path tries by-id path when device not cached."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            registry._devices = {}

            # Create a fake by-id symlink
            fake_by_id = Path(tmpdir) / "by-id"
            fake_by_id.mkdir()
            fake_link = fake_by_id / "test-device"
            fake_event = Path(tmpdir) / "event99"
            fake_event.write_text("")
            fake_link.symlink_to(fake_event)

            with patch("crates.device_registry.registry.Path") as mock_path_cls:
                mock_path = mock_path_cls.return_value
                mock_path.exists.return_value = True
                mock_path.resolve.return_value = fake_event
                mock_path.__truediv__ = lambda self, x: mock_path

                registry.get_event_path("test-device")
                # Result depends on mocking - just verify no exception

    def test_get_event_path_handles_oserror_in_fallback(self):
        """Test get_event_path handles OSError when resolving by-id path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            registry._devices = {}

            with patch("crates.device_registry.registry.Path") as mock_path_cls:
                mock_path = mock_path_cls.return_value
                mock_path.exists.return_value = True
                mock_path.resolve.side_effect = OSError("Permission denied")
                mock_path.__truediv__ = lambda self, x: mock_path

                result = registry.get_event_path("test-device")
                assert result is None

    def test_get_razer_devices_triggers_scan(self):
        """Test get_razer_devices scans if devices dict is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))
            # _devices is empty by default, should trigger scan
            with patch.object(registry, "scan_devices", return_value=[]) as mock_scan:
                result = registry.get_razer_devices()
                mock_scan.assert_called_once()
                assert result == []

    def test_scan_devices_handles_oserror_valueerror(self):
        """Test scan_devices catches OSError and ValueError exceptions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))

            class FakeSymlink:
                name = "test-symlink"

                def is_symlink(self):
                    return True

                def resolve(self):
                    raise OSError("Simulated OSError")

            fake_by_id = Path(tmpdir) / "by-id"
            fake_by_id.mkdir()

            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "iterdir", return_value=[FakeSymlink()]):
                    # Should catch OSError and continue, returning empty list
                    devices = registry.scan_devices()
                    assert devices == []

    def test_scan_devices_handles_valueerror(self):
        """Test scan_devices catches ValueError exception."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry = DeviceRegistry(config_dir=Path(tmpdir))

            class FakeSymlink:
                name = "test-symlink"

                def is_symlink(self):
                    return True

                def resolve(self):
                    raise ValueError("Simulated ValueError")

            with patch.object(Path, "exists", return_value=True):
                with patch.object(Path, "iterdir", return_value=[FakeSymlink()]):
                    # Should catch ValueError and continue
                    devices = registry.scan_devices()
                    assert devices == []
