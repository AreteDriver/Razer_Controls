"""Keycode mapping between evdev, schema names, and uinput."""

from .mapping import (
    # Core mappings
    EVDEV_TO_SCHEMA,
    SCHEMA_TO_EVDEV,
    SCHEMA_TO_UINPUT,
    KEY_CATEGORIES,
    # Conversion functions
    evdev_code_to_schema,
    schema_to_evdev_code,
    schema_to_evdev_name,
    evdev_event_to_schema,
    # Query functions
    get_all_schema_keys,
    get_all_evdev_keys,
    get_keys_by_category,
    get_key_info,
    # Validation
    is_valid_key,
    validate_key,
)

__all__ = [
    # Core mappings
    "EVDEV_TO_SCHEMA",
    "SCHEMA_TO_EVDEV",
    "SCHEMA_TO_UINPUT",
    "KEY_CATEGORIES",
    # Conversion functions
    "evdev_code_to_schema",
    "schema_to_evdev_code",
    "schema_to_evdev_name",
    "evdev_event_to_schema",
    # Query functions
    "get_all_schema_keys",
    "get_all_evdev_keys",
    "get_keys_by_category",
    "get_key_info",
    # Validation
    "is_valid_key",
    "validate_key",
]
