"""Tests for the profile loader."""

import json
import tempfile
from pathlib import Path

import pytest

from crates.profile_schema import Profile, ProfileLoader
from crates.profile_schema.schema import ActionType, Binding, Layer, MacroAction, MacroStep, MacroStepType


class TestProfileLoader:
    """Tests for ProfileLoader class."""

    def test_init_default_config_dir(self):
        """Test loader uses default config dir."""
        loader = ProfileLoader()
        assert loader.config_dir == Path.home() / ".config" / "razer-control-center"

    def test_init_custom_config_dir(self):
        """Test loader with custom config dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir)
            loader = ProfileLoader(config_dir=config_dir)
            assert loader.config_dir == config_dir
            assert loader.profiles_dir == config_dir / "profiles"

    def test_ensure_dirs_creates_directories(self):
        """Test that _ensure_dirs creates required directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "new_config"
            loader = ProfileLoader(config_dir=config_dir)
            assert config_dir.exists()
            assert loader.profiles_dir.exists()

    def test_list_profiles_empty(self):
        """Test listing profiles when none exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))
            profiles = loader.list_profiles()
            assert profiles == []

    def test_list_profiles_with_profiles(self):
        """Test listing profiles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))
            # Create some profile files
            (loader.profiles_dir / "profile1.json").write_text("{}")
            (loader.profiles_dir / "profile2.json").write_text("{}")
            (loader.profiles_dir / "default.json").write_text("{}")

            profiles = loader.list_profiles()
            assert sorted(profiles) == ["default", "profile1", "profile2"]

    def test_save_and_load_profile(self):
        """Test saving and loading a profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))

            # Create a profile
            profile = Profile(
                id="test-profile",
                name="Test Profile",
                input_devices=["device1"],
                is_default=True,
            )

            # Save it
            result = loader.save_profile(profile)
            assert result is True
            assert (loader.profiles_dir / "test-profile.json").exists()

            # Load it back
            loaded = loader.load_profile("test-profile")
            assert loaded is not None
            assert loaded.id == "test-profile"
            assert loaded.name == "Test Profile"
            assert loaded.is_default is True

    def test_load_profile_not_found(self):
        """Test loading a profile that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))
            profile = loader.load_profile("nonexistent")
            assert profile is None

    def test_load_profile_invalid_json(self):
        """Test loading a profile with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))
            (loader.profiles_dir / "invalid.json").write_text("not valid json")

            profile = loader.load_profile("invalid")
            assert profile is None

    def test_delete_profile(self):
        """Test deleting a profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))

            # Create a profile
            profile_path = loader.profiles_dir / "to-delete.json"
            profile_path.write_text("{}")
            assert profile_path.exists()

            # Delete it
            result = loader.delete_profile("to-delete")
            assert result is True
            assert not profile_path.exists()

    def test_delete_profile_not_found(self):
        """Test deleting a profile that doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))
            result = loader.delete_profile("nonexistent")
            assert result is False

    def test_get_active_profile_path(self):
        """Test getting active profile path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))
            path = loader.get_active_profile_path()
            assert path == Path(tmpdir) / "active_profile"

    def test_set_and_get_active_profile(self):
        """Test setting and getting active profile ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))

            # Initially no active profile
            assert loader.get_active_profile_id() is None

            # Set active profile
            loader.set_active_profile("my-profile")
            assert loader.get_active_profile_id() == "my-profile"

    def test_load_active_profile(self):
        """Test loading the active profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))

            # Create and save a profile
            profile = Profile(
                id="active-test",
                name="Active Test",
                input_devices=[],
            )
            loader.save_profile(profile)

            # Set it as active
            loader.set_active_profile("active-test")

            # Load active profile
            loaded = loader.load_active_profile()
            assert loaded is not None
            assert loaded.id == "active-test"

    def test_load_active_profile_fallback_to_default(self):
        """Test loading active profile falls back to default."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))

            # Create a default profile
            profile = Profile(
                id="default-profile",
                name="Default",
                input_devices=[],
                is_default=True,
            )
            loader.save_profile(profile)

            # No active profile set - should fall back to default
            loaded = loader.load_active_profile()
            assert loaded is not None
            assert loaded.id == "default-profile"
            assert loaded.is_default is True

    def test_load_active_profile_no_profiles(self):
        """Test loading active profile when none exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))
            loaded = loader.load_active_profile()
            assert loaded is None

    def test_save_and_load_global_macros(self):
        """Test saving and loading global macros."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))

            # Create macros
            macros = [
                MacroAction(
                    id="macro1",
                    name="Copy Paste",
                    steps=[
                        MacroStep(type=MacroStepType.KEY_PRESS, key="c"),
                        MacroStep(type=MacroStepType.DELAY, delay_ms=100),
                        MacroStep(type=MacroStepType.KEY_PRESS, key="v"),
                    ],
                ),
                MacroAction(
                    id="macro2",
                    name="Type Hello",
                    steps=[
                        MacroStep(type=MacroStepType.TEXT, text="Hello World"),
                    ],
                ),
            ]

            # Save
            result = loader.save_global_macros(macros)
            assert result is True

            # Load
            loaded = loader.load_global_macros()
            assert len(loaded) == 2
            assert loaded[0].name == "Copy Paste"
            assert loaded[1].name == "Type Hello"

    def test_load_global_macros_no_file(self):
        """Test loading macros when no file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))
            macros = loader.load_global_macros()
            assert macros == []

    def test_load_global_macros_invalid_json(self):
        """Test loading macros with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))
            loader.macros_file.write_text("not valid json")

            macros = loader.load_global_macros()
            assert macros == []

    def test_profile_with_layers_and_bindings(self):
        """Test saving and loading a profile with layers and bindings."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))

            # Create a profile with bindings
            profile = Profile(
                id="gaming-profile",
                name="Gaming",
                input_devices=["usb-Razer_Mouse-event-mouse"],
                layers=[
                    Layer(
                        id="layer-default",
                        name="Default",
                        bindings=[
                            Binding(
                                input_code="BTN_SIDE",
                                action_type=ActionType.KEY,
                                output_keys=["KEY_F13"],
                            ),
                            Binding(
                                input_code="BTN_EXTRA",
                                action_type=ActionType.CHORD,
                                output_keys=["KEY_LEFTCTRL", "KEY_C"],
                            ),
                        ],
                    ),
                ],
            )

            # Save and load
            loader.save_profile(profile)
            loaded = loader.load_profile("gaming-profile")

            assert loaded is not None
            assert len(loaded.layers) == 1
            assert len(loaded.layers[0].bindings) == 2
            assert loaded.layers[0].bindings[0].input_code == "BTN_SIDE"
            assert loaded.layers[0].bindings[0].action_type == ActionType.KEY

    def test_profile_with_match_process_names(self):
        """Test profile with app matching patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = ProfileLoader(config_dir=Path(tmpdir))

            profile = Profile(
                id="app-profile",
                name="App Specific",
                input_devices=[],
                match_process_names=["firefox", "chrome*", "*.exe"],
            )

            loader.save_profile(profile)
            loaded = loader.load_profile("app-profile")

            assert loaded is not None
            assert loaded.match_process_names == ["firefox", "chrome*", "*.exe"]
