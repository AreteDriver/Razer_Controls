"""Tests for tools/keymap_check.py - Keycode checker CLI."""

import json
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.keymap_check import cmd_check, cmd_info, cmd_list, cmd_validate, main


class TestCmdList:
    """Tests for cmd_list function."""

    def test_list_by_category(self, capsys):
        """Test listing keys by category."""
        args = Namespace(category="Modifiers", evdev=False, categories=False)
        result = cmd_list(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Modifiers Keys:" in captured.out

    def test_list_unknown_category(self, capsys):
        """Test listing with unknown category."""
        args = Namespace(category="UnknownCategory", evdev=False, categories=False)
        result = cmd_list(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Unknown category: UnknownCategory" in captured.out
        assert "Available categories:" in captured.out

    def test_list_evdev_keys(self, capsys):
        """Test listing all evdev key names."""
        args = Namespace(category=None, evdev=True, categories=False)
        result = cmd_list(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "All evdev key names:" in captured.out
        assert "Total:" in captured.out

    def test_list_categories(self, capsys):
        """Test listing available categories."""
        args = Namespace(category=None, evdev=False, categories=True)
        result = cmd_list(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Available categories:" in captured.out
        # Check for at least one category
        assert "keys)" in captured.out

    def test_list_all_schema_keys(self, capsys):
        """Test listing all schema key names (default)."""
        args = Namespace(category=None, evdev=False, categories=False)
        result = cmd_list(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "All schema key names (human-friendly):" in captured.out
        assert "Total:" in captured.out


class TestCmdInfo:
    """Tests for cmd_info function."""

    def test_info_valid_key(self, capsys):
        """Test getting info for a valid key."""
        args = Namespace(key="A")
        result = cmd_info(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Key Information: A" in captured.out
        assert "Schema name:" in captured.out
        assert "evdev name:" in captured.out
        assert "Code:" in captured.out
        assert "Category:" in captured.out

    def test_info_valid_modifier(self, capsys):
        """Test getting info for a modifier key."""
        args = Namespace(key="CTRL")
        result = cmd_info(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Key Information: CTRL" in captured.out

    def test_info_invalid_key(self, capsys):
        """Test getting info for an invalid key."""
        args = Namespace(key="INVALID_KEY_XYZ")
        result = cmd_info(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Error:" in captured.out


class TestCmdCheck:
    """Tests for cmd_check function."""

    def test_check_valid_single_key(self, capsys):
        """Test checking a valid single key."""
        args = Namespace(chord="A")
        result = cmd_check(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Checking: A" in captured.out
        assert "✓" in captured.out
        assert "Valid chord:" in captured.out

    def test_check_valid_chord(self, capsys):
        """Test checking a valid key chord."""
        args = Namespace(chord="CTRL+SHIFT+A")
        result = cmd_check(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Checking: CTRL+SHIFT+A" in captured.out
        assert "✓ Valid chord:" in captured.out

    def test_check_invalid_key(self, capsys):
        """Test checking an invalid key."""
        args = Namespace(chord="INVALID_KEY")
        result = cmd_check(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "✗" in captured.out
        assert "Invalid chord" in captured.out

    def test_check_partially_valid_chord(self, capsys):
        """Test checking a chord with one invalid key."""
        args = Namespace(chord="CTRL+INVALID")
        result = cmd_check(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "✓" in captured.out  # CTRL is valid
        assert "✗" in captured.out  # INVALID is not
        assert "Invalid chord" in captured.out


class TestCmdValidate:
    """Tests for cmd_validate function."""

    def test_validate_missing_file(self, capsys):
        """Test validating a non-existent file."""
        args = Namespace(profile="/nonexistent/profile.json")
        result = cmd_validate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "File not found" in captured.out

    def test_validate_invalid_json(self, tmp_path, capsys):
        """Test validating an invalid JSON file."""
        profile_path = tmp_path / "invalid.json"
        profile_path.write_text("{ invalid json }")
        args = Namespace(profile=str(profile_path))
        result = cmd_validate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Invalid JSON" in captured.out

    def test_validate_missing_required_fields(self, tmp_path, capsys):
        """Test validating profile missing required fields."""
        profile_path = tmp_path / "missing_fields.json"
        profile_path.write_text(json.dumps({}))
        args = Namespace(profile=str(profile_path))
        result = cmd_validate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Missing required field: id" in captured.out
        assert "Missing required field: name" in captured.out
        assert "Missing required field: layers" in captured.out

    def test_validate_empty_layers_warning(self, tmp_path, capsys):
        """Test validating profile with empty layers."""
        profile = {"id": "test", "name": "Test Profile", "layers": []}
        profile_path = tmp_path / "empty_layers.json"
        profile_path.write_text(json.dumps(profile))
        args = Namespace(profile=str(profile_path))
        result = cmd_validate(args)
        assert result == 0  # Warning, not error
        captured = capsys.readouterr()
        assert "no layers defined" in captured.out
        assert "0 errors" in captured.out

    def test_validate_duplicate_layer_id(self, tmp_path, capsys):
        """Test validating profile with duplicate layer IDs."""
        profile = {
            "id": "test",
            "name": "Test Profile",
            "layers": [
                {"id": "layer1", "name": "Layer 1"},
                {"id": "layer1", "name": "Layer 1 Duplicate"},
            ],
        }
        profile_path = tmp_path / "dup_layers.json"
        profile_path.write_text(json.dumps(profile))
        args = Namespace(profile=str(profile_path))
        result = cmd_validate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Duplicate layer ID: layer1" in captured.out

    def test_validate_invalid_hold_modifier(self, tmp_path, capsys):
        """Test validating profile with invalid hold modifier."""
        profile = {
            "id": "test",
            "name": "Test Profile",
            "layers": [{"id": "layer1", "name": "Layer 1", "hold_modifier_input_code": "INVALID_KEY"}],
        }
        profile_path = tmp_path / "bad_modifier.json"
        profile_path.write_text(json.dumps(profile))
        args = Namespace(profile=str(profile_path))
        result = cmd_validate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "hold modifier" in captured.out

    def test_validate_missing_input_code(self, tmp_path, capsys):
        """Test validating binding without input_code."""
        profile = {
            "id": "test",
            "name": "Test Profile",
            "layers": [{"id": "layer1", "name": "Layer 1", "bindings": [{}]}],
        }
        profile_path = tmp_path / "no_input.json"
        profile_path.write_text(json.dumps(profile))
        args = Namespace(profile=str(profile_path))
        result = cmd_validate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Missing input_code" in captured.out

    def test_validate_invalid_input_code(self, tmp_path, capsys):
        """Test validating binding with invalid input_code."""
        profile = {
            "id": "test",
            "name": "Test Profile",
            "layers": [{"id": "layer1", "name": "Layer 1", "bindings": [{"input_code": "INVALID"}]}],
        }
        profile_path = tmp_path / "bad_input.json"
        profile_path.write_text(json.dumps(profile))
        args = Namespace(profile=str(profile_path))
        result = cmd_validate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "input_code:" in captured.out

    def test_validate_invalid_output_key(self, tmp_path, capsys):
        """Test validating binding with invalid output_keys."""
        profile = {
            "id": "test",
            "name": "Test Profile",
            "layers": [
                {
                    "id": "layer1",
                    "name": "Layer 1",
                    "bindings": [{"input_code": "A", "output_keys": ["INVALID_OUTPUT"]}],
                }
            ],
        }
        profile_path = tmp_path / "bad_output.json"
        profile_path.write_text(json.dumps(profile))
        args = Namespace(profile=str(profile_path))
        result = cmd_validate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "output_key" in captured.out

    def test_validate_unknown_action_type_warning(self, tmp_path, capsys):
        """Test validating binding with unknown action_type."""
        profile = {
            "id": "test",
            "name": "Test Profile",
            "layers": [
                {
                    "id": "layer1",
                    "name": "Layer 1",
                    "bindings": [{"input_code": "A", "action_type": "unknown_type"}],
                }
            ],
        }
        profile_path = tmp_path / "bad_action.json"
        profile_path.write_text(json.dumps(profile))
        args = Namespace(profile=str(profile_path))
        result = cmd_validate(args)
        assert result == 0  # Warning, not error
        captured = capsys.readouterr()
        assert "Unknown action_type" in captured.out
        assert "Warnings:" in captured.out

    def test_validate_missing_macro_reference(self, tmp_path, capsys):
        """Test validating binding referencing nonexistent macro."""
        profile = {
            "id": "test",
            "name": "Test Profile",
            "layers": [
                {
                    "id": "layer1",
                    "name": "Layer 1",
                    "bindings": [{"input_code": "A", "action_type": "macro", "macro_id": "missing_macro"}],
                }
            ],
            "macros": [],
        }
        profile_path = tmp_path / "bad_macro_ref.json"
        profile_path.write_text(json.dumps(profile))
        args = Namespace(profile=str(profile_path))
        result = cmd_validate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "macro 'missing_macro' not found" in captured.out

    def test_validate_macro_missing_id(self, tmp_path, capsys):
        """Test validating macro without id."""
        profile = {
            "id": "test",
            "name": "Test Profile",
            "layers": [],
            "macros": [{"name": "Test Macro"}],
        }
        profile_path = tmp_path / "macro_no_id.json"
        profile_path.write_text(json.dumps(profile))
        args = Namespace(profile=str(profile_path))
        result = cmd_validate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Macro 1: Missing id" in captured.out

    def test_validate_macro_invalid_step_key(self, tmp_path, capsys):
        """Test validating macro with invalid step key."""
        profile = {
            "id": "test",
            "name": "Test Profile",
            "layers": [],
            "macros": [{"id": "test_macro", "steps": [{"key": "INVALID_STEP_KEY"}]}],
        }
        profile_path = tmp_path / "macro_bad_key.json"
        profile_path.write_text(json.dumps(profile))
        args = Namespace(profile=str(profile_path))
        result = cmd_validate(args)
        assert result == 1
        captured = capsys.readouterr()
        assert "Macro 'test_macro'" in captured.out

    def test_validate_valid_profile(self, tmp_path, capsys):
        """Test validating a fully valid profile."""
        profile = {
            "id": "valid_profile",
            "name": "Valid Profile",
            "layers": [
                {
                    "id": "base",
                    "name": "Base Layer",
                    "bindings": [
                        {"input_code": "A", "output_keys": ["B"], "action_type": "key"},
                        {"input_code": "C", "action_type": "macro", "macro_id": "test_macro"},
                    ],
                }
            ],
            "macros": [{"id": "test_macro", "name": "Test Macro", "steps": [{"key": "D"}]}],
        }
        profile_path = tmp_path / "valid.json"
        profile_path.write_text(json.dumps(profile))
        args = Namespace(profile=str(profile_path))
        result = cmd_validate(args)
        assert result == 0
        captured = capsys.readouterr()
        assert "Profile is valid" in captured.out
        assert "0 errors, 0 warnings" in captured.out


class TestMain:
    """Tests for main function."""

    def test_main_no_args(self, capsys):
        """Test main with no arguments prints help."""
        with patch.object(sys, "argv", ["keymap_check"]):
            result = main()
        assert result == 0
        captured = capsys.readouterr()
        assert "usage:" in captured.out

    def test_main_list(self, capsys):
        """Test main with --list flag."""
        with patch.object(sys, "argv", ["keymap_check", "--list"]):
            result = main()
        assert result == 0
        captured = capsys.readouterr()
        assert "All schema key names" in captured.out

    def test_main_list_categories(self, capsys):
        """Test main with --categories flag."""
        with patch.object(sys, "argv", ["keymap_check", "--categories"]):
            result = main()
        assert result == 0
        captured = capsys.readouterr()
        assert "Available categories:" in captured.out

    def test_main_list_evdev(self, capsys):
        """Test main with --list --evdev flags."""
        with patch.object(sys, "argv", ["keymap_check", "--list", "--evdev"]):
            result = main()
        assert result == 0
        captured = capsys.readouterr()
        assert "All evdev key names:" in captured.out

    def test_main_list_category(self, capsys):
        """Test main with --list --category flags."""
        with patch.object(sys, "argv", ["keymap_check", "--list", "--category", "Modifiers"]):
            result = main()
        assert result == 0
        captured = capsys.readouterr()
        assert "Modifiers Keys:" in captured.out

    def test_main_info(self, capsys):
        """Test main with --info flag."""
        with patch.object(sys, "argv", ["keymap_check", "--info", "CTRL"]):
            result = main()
        assert result == 0
        captured = capsys.readouterr()
        assert "Key Information: CTRL" in captured.out

    def test_main_check(self, capsys):
        """Test main with --check flag."""
        with patch.object(sys, "argv", ["keymap_check", "--check", "CTRL+A"]):
            result = main()
        assert result == 0
        captured = capsys.readouterr()
        assert "Valid chord:" in captured.out

    def test_main_validate(self, tmp_path, capsys):
        """Test main with --validate flag."""
        profile = {"id": "test", "name": "Test", "layers": []}
        profile_path = tmp_path / "profile.json"
        profile_path.write_text(json.dumps(profile))
        with patch.object(sys, "argv", ["keymap_check", "--validate", str(profile_path)]):
            result = main()
        assert result == 0


class TestMainGuard:
    """Test the __name__ == '__main__' guard."""

    def test_main_guard_exists(self):
        """Verify the main guard exists in the source file."""
        from tools import keymap_check

        source = Path(keymap_check.__file__).read_text()
        assert 'if __name__ == "__main__":' in source
