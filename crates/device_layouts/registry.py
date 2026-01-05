"""Registry for loading and matching device layouts."""

import json
import logging
import re
from pathlib import Path

from .schema import DeviceCategory, DeviceLayout

logger = logging.getLogger(__name__)


class DeviceLayoutRegistry:
    """Singleton registry for device layouts.

    Loads layouts from JSON files and matches devices to layouts
    using regex patterns on device names.
    """

    _instance: "DeviceLayoutRegistry | None" = None
    _initialized: bool = False

    def __new__(cls) -> "DeviceLayoutRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if DeviceLayoutRegistry._initialized:
            return
        DeviceLayoutRegistry._initialized = True

        self._layouts: dict[str, DeviceLayout] = {}
        self._pattern_cache: list[tuple[re.Pattern[str], str]] = []
        self._data_dir: Path | None = None

    def load_layouts(self, data_dir: Path | None = None) -> None:
        """Load all layouts from the data directory.

        Args:
            data_dir: Directory containing device layout JSON files.
                     Defaults to data/device_layouts/ in project root.
        """
        if data_dir is None:
            # Find data directory relative to this module
            module_dir = Path(__file__).parent.parent.parent
            data_dir = module_dir / "data" / "device_layouts"

        self._data_dir = data_dir
        self._layouts.clear()
        self._pattern_cache.clear()

        if not data_dir.exists():
            logger.warning(f"Device layouts directory not found: {data_dir}")
            return

        # Load all JSON files from subdirectories
        for json_file in data_dir.rglob("*.json"):
            try:
                self._load_layout_file(json_file)
            except Exception as e:
                logger.error(f"Failed to load layout {json_file}: {e}")

        logger.info(f"Loaded {len(self._layouts)} device layouts")

    def _load_layout_file(self, path: Path) -> None:
        """Load a single layout file."""
        with open(path) as f:
            data = json.load(f)

        layout = DeviceLayout.from_dict(data)
        self._layouts[layout.id] = layout

        # Cache compiled regex patterns
        for pattern_str in layout.device_name_patterns:
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE)
                self._pattern_cache.append((pattern, layout.id))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern_str}': {e}")

    def get_layout(self, layout_id: str) -> DeviceLayout | None:
        """Get a layout by its ID."""
        return self._layouts.get(layout_id)

    def get_layout_for_device(
        self,
        device_name: str,
        device_type: str | None = None,
        matrix_cols: int | None = None,
    ) -> DeviceLayout | None:
        """Find the best layout for a device.

        Matching strategy:
        1. Try regex patterns against device name
        2. Use device type to select generic layout
        3. Use matrix dimensions to guess device type
        4. Return None if no match found

        Args:
            device_name: Name of the device (e.g., "Razer DeathAdder V2")
            device_type: Optional device type string
            matrix_cols: Optional matrix column count for fallback

        Returns:
            DeviceLayout if found, None otherwise
        """
        # Try pattern matching first
        for pattern, layout_id in self._pattern_cache:
            if pattern.search(device_name):
                return self._layouts[layout_id]

        # Try device type heuristic
        if device_type:
            device_type_lower = device_type.lower()
            if "mouse" in device_type_lower:
                return self._layouts.get("generic_mouse")
            if "keyboard" in device_type_lower:
                return self._layouts.get("generic_keyboard")
            if "keypad" in device_type_lower:
                return self._layouts.get("generic_keypad")

        # Try matrix dimensions
        if matrix_cols is not None and isinstance(matrix_cols, int):
            if matrix_cols < 6:
                return self._layouts.get("generic_mouse")
            if matrix_cols < 12:
                return self._layouts.get("generic_keypad")
            return self._layouts.get("generic_keyboard")

        return None

    def list_layouts(self) -> list[DeviceLayout]:
        """Get all loaded layouts."""
        return list(self._layouts.values())

    def list_layouts_by_category(self, category: DeviceCategory) -> list[DeviceLayout]:
        """Get all layouts for a specific category."""
        return [layout for layout in self._layouts.values() if layout.category == category]

    def reload(self) -> None:
        """Reload all layouts from disk."""
        if self._data_dir:
            DeviceLayoutRegistry._initialized = False
            self.__init__()
            self.load_layouts(self._data_dir)


def get_registry() -> DeviceLayoutRegistry:
    """Get the singleton registry instance."""
    registry = DeviceLayoutRegistry()
    if not registry._layouts:
        registry.load_layouts()
    return registry
