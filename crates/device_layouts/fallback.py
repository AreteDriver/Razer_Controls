"""Fallback layouts for devices without specific definitions."""

from .schema import ButtonShape, DeviceCategory, DeviceLayout, ShapeType


def get_generic_mouse_layout() -> DeviceLayout:
    """Create a generic mouse layout.

    Standard layout with:
    - Left/Right click buttons
    - Scroll wheel (up/down/click)
    - Two side buttons
    - DPI button
    - Logo zone (RGB)
    """
    return DeviceLayout(
        id="generic_mouse",
        name="Generic Mouse",
        category=DeviceCategory.MOUSE,
        device_name_patterns=[],
        base_width=80,
        base_height=140,
        outline_path=[
            # Mouse body outline (teardrop shape)
            (0.5, 0.0),  # Top center
            (0.85, 0.15),  # Top right curve
            (1.0, 0.4),  # Right side
            (0.95, 0.7),  # Right lower
            (0.8, 0.9),  # Bottom right
            (0.5, 1.0),  # Bottom center
            (0.2, 0.9),  # Bottom left
            (0.05, 0.7),  # Left lower
            (0.0, 0.4),  # Left side
            (0.15, 0.15),  # Top left curve
        ],
        buttons=[
            # Left click
            ButtonShape(
                id="left_click",
                label="Left Click",
                x=0.08,
                y=0.05,
                width=0.38,
                height=0.30,
                shape_type=ShapeType.RECT,
                input_code="BTN_LEFT",
            ),
            # Right click
            ButtonShape(
                id="right_click",
                label="Right Click",
                x=0.54,
                y=0.05,
                width=0.38,
                height=0.30,
                shape_type=ShapeType.RECT,
                input_code="BTN_RIGHT",
            ),
            # Scroll wheel
            ButtonShape(
                id="scroll_wheel",
                label="Scroll Wheel",
                x=0.38,
                y=0.12,
                width=0.24,
                height=0.18,
                shape_type=ShapeType.ELLIPSE,
                input_code="BTN_MIDDLE",
            ),
            # DPI button
            ButtonShape(
                id="dpi_button",
                label="DPI",
                x=0.38,
                y=0.35,
                width=0.24,
                height=0.08,
                shape_type=ShapeType.RECT,
            ),
            # Side button 1 (forward)
            ButtonShape(
                id="side_forward",
                label="Forward",
                x=0.0,
                y=0.42,
                width=0.12,
                height=0.12,
                shape_type=ShapeType.RECT,
                input_code="BTN_FORWARD",
            ),
            # Side button 2 (back)
            ButtonShape(
                id="side_back",
                label="Back",
                x=0.0,
                y=0.56,
                width=0.12,
                height=0.12,
                shape_type=ShapeType.RECT,
                input_code="BTN_BACK",
            ),
            # Logo zone (RGB)
            ButtonShape(
                id="logo_zone",
                label="Logo",
                x=0.30,
                y=0.60,
                width=0.40,
                height=0.15,
                shape_type=ShapeType.ELLIPSE,
                is_zone=True,
            ),
        ],
    )


def get_generic_keyboard_layout() -> DeviceLayout:
    """Create a generic keyboard layout.

    Uses zones instead of individual keys for practical interaction.
    Zones match the typical OpenRazer zone definitions.
    """
    return DeviceLayout(
        id="generic_keyboard",
        name="Generic Keyboard",
        category=DeviceCategory.KEYBOARD,
        device_name_patterns=[],
        base_width=450,
        base_height=150,
        outline_path=[
            (0.0, 0.0),
            (1.0, 0.0),
            (1.0, 1.0),
            (0.0, 1.0),
        ],
        buttons=[
            # Function row zone
            ButtonShape(
                id="zone_function",
                label="Function Keys",
                x=0.18,
                y=0.05,
                width=0.58,
                height=0.15,
                shape_type=ShapeType.RECT,
                is_zone=True,
            ),
            # Number row zone
            ButtonShape(
                id="zone_numbers",
                label="Number Row",
                x=0.02,
                y=0.22,
                width=0.82,
                height=0.15,
                shape_type=ShapeType.RECT,
                is_zone=True,
            ),
            # QWERTY zone
            ButtonShape(
                id="zone_qwerty",
                label="QWERTY",
                x=0.02,
                y=0.39,
                width=0.80,
                height=0.15,
                shape_type=ShapeType.RECT,
                is_zone=True,
            ),
            # Home row zone (ASDF)
            ButtonShape(
                id="zone_home",
                label="Home Row",
                x=0.02,
                y=0.56,
                width=0.78,
                height=0.15,
                shape_type=ShapeType.RECT,
                is_zone=True,
            ),
            # Bottom row zone
            ButtonShape(
                id="zone_bottom",
                label="Bottom Row",
                x=0.02,
                y=0.73,
                width=0.78,
                height=0.15,
                shape_type=ShapeType.RECT,
                is_zone=True,
            ),
            # Arrow keys zone
            ButtonShape(
                id="zone_arrows",
                label="Arrows",
                x=0.82,
                y=0.56,
                width=0.16,
                height=0.32,
                shape_type=ShapeType.RECT,
                is_zone=True,
            ),
            # Numpad zone
            ButtonShape(
                id="zone_numpad",
                label="Numpad",
                x=0.86,
                y=0.22,
                width=0.12,
                height=0.32,
                shape_type=ShapeType.RECT,
                is_zone=True,
            ),
            # Logo zone
            ButtonShape(
                id="zone_logo",
                label="Logo",
                x=0.02,
                y=0.05,
                width=0.12,
                height=0.15,
                shape_type=ShapeType.ELLIPSE,
                is_zone=True,
            ),
        ],
    )


def get_generic_keypad_layout() -> DeviceLayout:
    """Create a generic keypad layout.

    Similar to Razer Tartarus with:
    - 20 programmable keys in a 5x4 grid
    - Thumbstick area
    - Palm rest area
    """
    buttons = []

    # Create 5x4 key grid
    for row in range(4):
        for col in range(5):
            key_num = row * 5 + col + 1
            buttons.append(
                ButtonShape(
                    id=f"key_{key_num:02d}",
                    label=f"Key {key_num}",
                    x=0.08 + col * 0.17,
                    y=0.08 + row * 0.18,
                    width=0.14,
                    height=0.14,
                    shape_type=ShapeType.RECT,
                    input_code=f"KEY_{key_num}",
                )
            )

    # Thumbstick
    buttons.append(
        ButtonShape(
            id="thumbstick",
            label="Thumbstick",
            x=0.35,
            y=0.82,
            width=0.30,
            height=0.15,
            shape_type=ShapeType.ELLIPSE,
        )
    )

    # Thumb button
    buttons.append(
        ButtonShape(
            id="thumb_button",
            label="Thumb",
            x=0.70,
            y=0.82,
            width=0.20,
            height=0.15,
            shape_type=ShapeType.RECT,
            input_code="BTN_THUMB",
        )
    )

    return DeviceLayout(
        id="generic_keypad",
        name="Generic Keypad",
        category=DeviceCategory.KEYPAD,
        device_name_patterns=[],
        base_width=180,
        base_height=200,
        outline_path=[
            (0.0, 0.0),
            (1.0, 0.0),
            (1.0, 0.75),
            (0.85, 0.75),
            (0.85, 1.0),
            (0.15, 1.0),
            (0.15, 0.75),
            (0.0, 0.75),
        ],
        buttons=buttons,
    )


def get_fallback_layout(
    device_type: str | None = None,
    matrix_cols: int | None = None,
) -> DeviceLayout:
    """Get a fallback layout based on device characteristics.

    Args:
        device_type: Device type string (e.g., "mouse", "keyboard")
        matrix_cols: Matrix column count for dimension-based detection

    Returns:
        Appropriate generic layout
    """
    # Try device type first
    if device_type:
        device_type_lower = device_type.lower()
        if "mouse" in device_type_lower:
            return get_generic_mouse_layout()
        if "keyboard" in device_type_lower:
            return get_generic_keyboard_layout()
        if "keypad" in device_type_lower:
            return get_generic_keypad_layout()

    # Try matrix dimensions
    if matrix_cols is not None and isinstance(matrix_cols, int):
        if matrix_cols < 6:
            return get_generic_mouse_layout()
        if matrix_cols < 12:
            return get_generic_keypad_layout()
        return get_generic_keyboard_layout()

    # Ultimate fallback
    return get_generic_mouse_layout()
