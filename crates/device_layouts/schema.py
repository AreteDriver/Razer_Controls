"""Data models for device layouts."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DeviceCategory(Enum):
    """Category of Razer device."""

    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    KEYPAD = "keypad"
    HEADSET = "headset"
    MOUSEPAD = "mousepad"
    UNKNOWN = "unknown"


class ShapeType(Enum):
    """Shape types for buttons."""

    RECT = "rect"
    ELLIPSE = "ellipse"
    POLYGON = "polygon"


@dataclass
class ButtonShape:
    """Represents a clickable button/zone on a device.

    Coordinates are relative (0-1) for scalable rendering.
    """

    id: str  # Unique identifier: "left_click", "scroll_up", "zone_wasd"
    label: str  # Display name: "Left Click", "Scroll Up"
    x: float  # Relative X position (0-1)
    y: float  # Relative Y position (0-1)
    width: float  # Relative width (0-1)
    height: float  # Relative height (0-1)
    shape_type: ShapeType = ShapeType.RECT
    input_code: str | None = None  # evdev code: "BTN_LEFT", "KEY_A"
    is_zone: bool = False  # True for RGB zones (not physical buttons)
    polygon_points: list[tuple[float, float]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ButtonShape":
        """Create ButtonShape from dict (JSON deserialization)."""
        shape_type = data.get("shape_type", "rect")
        if isinstance(shape_type, str):
            shape_type = ShapeType(shape_type)

        return cls(
            id=data["id"],
            label=data["label"],
            x=data["x"],
            y=data["y"],
            width=data["width"],
            height=data["height"],
            shape_type=shape_type,
            input_code=data.get("input_code"),
            is_zone=data.get("is_zone", False),
            polygon_points=data.get("polygon_points", []),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        result = {
            "id": self.id,
            "label": self.label,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "shape_type": self.shape_type.value,
        }
        if self.input_code:
            result["input_code"] = self.input_code
        if self.is_zone:
            result["is_zone"] = True
        if self.polygon_points:
            result["polygon_points"] = self.polygon_points
        return result


@dataclass
class DeviceLayout:
    """Complete layout definition for a device.

    Contains device metadata, outline shape, and all buttons/zones.
    """

    id: str  # "razer_deathadder_v2"
    name: str  # "Razer DeathAdder V2"
    category: DeviceCategory
    device_name_patterns: list[str]  # Regex patterns to match device names
    base_width: float  # Design width (for aspect ratio)
    base_height: float  # Design height
    outline_path: list[tuple[float, float]]  # Polygon outline (relative coords)
    buttons: list[ButtonShape] = field(default_factory=list)
    image_path: str | None = None  # Optional path to device image (relative to data/)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeviceLayout":
        """Create DeviceLayout from dict (JSON deserialization)."""
        category = data.get("category", "unknown")
        if isinstance(category, str):
            category = DeviceCategory(category)

        buttons = [ButtonShape.from_dict(b) for b in data.get("buttons", [])]

        return cls(
            id=data["id"],
            name=data["name"],
            category=category,
            device_name_patterns=data.get("device_name_patterns", []),
            base_width=data.get("base_width", 100),
            base_height=data.get("base_height", 200),
            outline_path=data.get("outline_path", []),
            buttons=buttons,
            image_path=data.get("image_path"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON serialization."""
        result = {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "device_name_patterns": self.device_name_patterns,
            "base_width": self.base_width,
            "base_height": self.base_height,
            "outline_path": self.outline_path,
            "buttons": [b.to_dict() for b in self.buttons],
        }
        if self.image_path:
            result["image_path"] = self.image_path
        return result

    def get_button(self, button_id: str) -> ButtonShape | None:
        """Get a button by ID."""
        for button in self.buttons:
            if button.id == button_id:
                return button
        return None

    def get_zones(self) -> list[ButtonShape]:
        """Get all RGB zones (is_zone=True)."""
        return [b for b in self.buttons if b.is_zone]

    def get_physical_buttons(self) -> list[ButtonShape]:
        """Get all physical buttons (is_zone=False)."""
        return [b for b in self.buttons if not b.is_zone]
