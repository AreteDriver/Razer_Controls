"""Unit tests for keycode mapping module."""

import pytest
from evdev import ecodes

from crates.keycode_map import (
    EVDEV_TO_SCHEMA,
    KEY_CATEGORIES,
    evdev_code_to_schema,
    evdev_event_to_schema,
    get_all_evdev_keys,
    get_all_schema_keys,
    get_key_info,
    get_keys_by_category,
    is_valid_key,
    schema_to_evdev_code,
    schema_to_evdev_name,
    validate_key,
)


class TestEvdevToSchema:
    """Test evdev -> schema name conversions."""

    def test_mouse_buttons(self):
        assert evdev_code_to_schema("BTN_LEFT") == "MOUSE_LEFT"
        assert evdev_code_to_schema("BTN_RIGHT") == "MOUSE_RIGHT"
        assert evdev_code_to_schema("BTN_MIDDLE") == "MOUSE_MIDDLE"
        assert evdev_code_to_schema("BTN_SIDE") == "MOUSE_SIDE"
        assert evdev_code_to_schema("BTN_EXTRA") == "MOUSE_EXTRA"

    def test_modifier_keys(self):
        assert evdev_code_to_schema("KEY_LEFTCTRL") == "CTRL"
        assert evdev_code_to_schema("KEY_RIGHTCTRL") == "CTRL_R"
        assert evdev_code_to_schema("KEY_LEFTSHIFT") == "SHIFT"
        assert evdev_code_to_schema("KEY_RIGHTSHIFT") == "SHIFT_R"
        assert evdev_code_to_schema("KEY_LEFTALT") == "ALT"
        assert evdev_code_to_schema("KEY_RIGHTALT") == "ALT_R"
        assert evdev_code_to_schema("KEY_LEFTMETA") == "META"

    def test_letter_keys(self):
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            assert evdev_code_to_schema(f"KEY_{letter}") == letter

    def test_number_keys(self):
        for i in range(10):
            assert evdev_code_to_schema(f"KEY_{i}") == str(i)

    def test_function_keys(self):
        for i in range(1, 13):
            assert evdev_code_to_schema(f"KEY_F{i}") == f"F{i}"

    def test_unknown_key_passthrough(self):
        # Unknown keys should return unchanged
        assert evdev_code_to_schema("UNKNOWN_KEY") == "UNKNOWN_KEY"

    def test_special_keys(self):
        assert evdev_code_to_schema("KEY_ESC") == "ESC"
        assert evdev_code_to_schema("KEY_TAB") == "TAB"
        assert evdev_code_to_schema("KEY_ENTER") == "ENTER"
        assert evdev_code_to_schema("KEY_SPACE") == "SPACE"
        assert evdev_code_to_schema("KEY_BACKSPACE") == "BACKSPACE"


class TestSchemaToEvdev:
    """Test schema name -> evdev code conversions."""

    def test_mouse_buttons(self):
        assert schema_to_evdev_code("MOUSE_LEFT") == ecodes.BTN_LEFT
        assert schema_to_evdev_code("MOUSE_RIGHT") == ecodes.BTN_RIGHT
        assert schema_to_evdev_code("MOUSE_MIDDLE") == ecodes.BTN_MIDDLE

    def test_modifier_keys(self):
        assert schema_to_evdev_code("CTRL") == ecodes.KEY_LEFTCTRL
        assert schema_to_evdev_code("SHIFT") == ecodes.KEY_LEFTSHIFT
        assert schema_to_evdev_code("ALT") == ecodes.KEY_LEFTALT
        assert schema_to_evdev_code("META") == ecodes.KEY_LEFTMETA

    def test_letter_keys(self):
        assert schema_to_evdev_code("A") == ecodes.KEY_A
        assert schema_to_evdev_code("Z") == ecodes.KEY_Z

    def test_number_keys(self):
        assert schema_to_evdev_code("0") == ecodes.KEY_0
        assert schema_to_evdev_code("9") == ecodes.KEY_9

    def test_function_keys(self):
        assert schema_to_evdev_code("F1") == ecodes.KEY_F1
        assert schema_to_evdev_code("F12") == ecodes.KEY_F12

    def test_evdev_name_directly(self):
        # Should accept evdev names directly
        assert schema_to_evdev_code("KEY_A") == ecodes.KEY_A
        assert schema_to_evdev_code("BTN_LEFT") == ecodes.BTN_LEFT

    def test_unknown_key_returns_none(self):
        assert schema_to_evdev_code("TOTALLY_INVALID") is None


class TestSchemaToEvdevName:
    """Test schema name -> evdev name conversions."""

    def test_returns_evdev_name(self):
        assert schema_to_evdev_name("CTRL") == "KEY_LEFTCTRL"
        assert schema_to_evdev_name("MOUSE_LEFT") == "BTN_LEFT"
        assert schema_to_evdev_name("A") == "KEY_A"

    def test_unknown_returns_none(self):
        assert schema_to_evdev_name("TOTALLY_INVALID") is None


class TestEvdevEventToSchema:
    """Test evdev event -> schema name conversions."""

    def test_key_event(self):
        # EV_KEY events should convert
        result = evdev_event_to_schema(ecodes.EV_KEY, ecodes.KEY_A)
        assert result == "A"

    def test_non_key_event(self):
        # Non-EV_KEY events return None
        result = evdev_event_to_schema(ecodes.EV_REL, ecodes.REL_X)
        assert result is None


class TestKeyCategories:
    """Test key category organization."""

    def test_categories_exist(self):
        expected = ["Mouse", "Modifiers", "Function", "Navigation", "Media", "System", "Numpad"]
        for cat in expected:
            assert cat in KEY_CATEGORIES

    def test_mouse_category(self):
        mouse_keys = KEY_CATEGORIES["Mouse"]
        assert "MOUSE_LEFT" in mouse_keys
        assert "MOUSE_RIGHT" in mouse_keys

    def test_modifiers_category(self):
        mod_keys = KEY_CATEGORIES["Modifiers"]
        assert "CTRL" in mod_keys
        assert "SHIFT" in mod_keys
        assert "ALT" in mod_keys

    def test_function_category(self):
        func_keys = KEY_CATEGORIES["Function"]
        assert "F1" in func_keys
        assert "F12" in func_keys

    def test_get_keys_by_category(self):
        categories = get_keys_by_category()
        # Should be a copy
        assert categories is not KEY_CATEGORIES
        assert categories == KEY_CATEGORIES


class TestKeyValidation:
    """Test key validation functions."""

    def test_is_valid_key_schema(self):
        assert is_valid_key("CTRL")
        assert is_valid_key("A")
        assert is_valid_key("MOUSE_LEFT")
        assert is_valid_key("F1")

    def test_is_valid_key_evdev(self):
        assert is_valid_key("KEY_A")
        assert is_valid_key("BTN_LEFT")

    def test_is_invalid_key(self):
        assert not is_valid_key("TOTALLY_INVALID_KEY_123")
        assert not is_valid_key("")

    def test_validate_key_valid(self):
        valid, msg = validate_key("CTRL")
        assert valid
        assert "Valid key" in msg
        assert "code=" in msg

    def test_validate_key_invalid(self):
        valid, msg = validate_key("INVALID")
        assert not valid
        assert "Unknown key" in msg

    def test_validate_key_empty(self):
        valid, msg = validate_key("")
        assert not valid
        assert "cannot be empty" in msg

    def test_validate_key_suggests_similar(self):
        valid, msg = validate_key("CTR")  # Missing L
        assert not valid
        assert "Did you mean" in msg
        assert "CTRL" in msg


class TestKeyInfo:
    """Test key info retrieval."""

    def test_get_key_info_schema(self):
        info = get_key_info("CTRL")
        assert info is not None
        assert info["schema_name"] == "CTRL"
        assert info["evdev_name"] == "KEY_LEFTCTRL"
        assert info["code"] == ecodes.KEY_LEFTCTRL
        assert info["category"] == "Modifiers"

    def test_get_key_info_evdev(self):
        info = get_key_info("KEY_A")
        assert info is not None
        assert info["code"] == ecodes.KEY_A

    def test_get_key_info_invalid(self):
        info = get_key_info("TOTALLY_INVALID")
        assert info is None

    def test_get_key_info_category_detection(self):
        info = get_key_info("MOUSE_LEFT")
        assert info["category"] == "Mouse"

        info = get_key_info("F1")
        assert info["category"] == "Function"


class TestKeyLists:
    """Test key list functions."""

    def test_get_all_schema_keys(self):
        keys = get_all_schema_keys()
        assert isinstance(keys, list)
        assert len(keys) > 100  # We have ~150 keys
        assert keys == sorted(keys)  # Should be sorted
        assert "A" in keys
        assert "CTRL" in keys
        assert "MOUSE_LEFT" in keys

    def test_get_all_evdev_keys(self):
        keys = get_all_evdev_keys()
        assert isinstance(keys, list)
        assert len(keys) > 100
        assert keys == sorted(keys)  # Should be sorted
        assert "KEY_A" in keys
        assert "BTN_LEFT" in keys


class TestMappingCompleteness:
    """Test that mappings are complete and consistent."""

    def test_all_schema_keys_have_codes(self):
        for key in get_all_schema_keys():
            code = schema_to_evdev_code(key)
            assert code is not None, f"Schema key '{key}' has no evdev code"

    def test_bidirectional_mapping(self):
        # evdev -> schema -> evdev code should work
        for evdev_name in get_all_evdev_keys():
            schema_name = evdev_code_to_schema(evdev_name)
            code = schema_to_evdev_code(schema_name)
            assert code is not None, f"Round-trip failed for {evdev_name} -> {schema_name}"

    def test_category_keys_are_valid(self):
        for cat_name, keys in KEY_CATEGORIES.items():
            for key in keys:
                assert is_valid_key(key), f"Category '{cat_name}' has invalid key '{key}'"

    def test_no_duplicate_schema_names(self):
        # All schema names should be unique
        schema_keys = list(EVDEV_TO_SCHEMA.values())
        assert len(schema_keys) == len(set(schema_keys)), "Duplicate schema names found"


class TestEdgeCases:
    """Test edge cases and special handling."""

    def test_case_handling(self):
        # Schema names are case-sensitive (uppercase)
        assert is_valid_key("A")
        # Lowercase won't be found directly but KEY_a doesn't exist in evdev
        assert not is_valid_key("a")

    def test_numpad_keys(self):
        assert schema_to_evdev_code("NUM_0") == ecodes.KEY_KP0
        assert schema_to_evdev_code("NUM_ENTER") == ecodes.KEY_KPENTER

    def test_media_keys(self):
        assert schema_to_evdev_code("PLAY_PAUSE") == ecodes.KEY_PLAYPAUSE
        assert schema_to_evdev_code("VOL_UP") == ecodes.KEY_VOLUMEUP
        assert schema_to_evdev_code("VOL_DOWN") == ecodes.KEY_VOLUMEDOWN


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
