"""Zone-based RGB editor for matrix lighting devices."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from crates.zone_definitions import (
    KeyboardLayout,
    Zone,
    get_layout_for_device,
    get_zones_for_preset,
)
from services.openrazer_bridge import OpenRazerBridge, RazerDevice


class ZoneColorButton(QPushButton):
    """Compact color button for zone items."""

    color_changed = Signal(tuple)  # Emits (r, g, b)

    def __init__(self, color: tuple = (0, 0, 0), parent=None):
        super().__init__(parent)
        self._color = color
        self._update_style()
        self.clicked.connect(self._pick_color)
        self.setFixedSize(50, 28)

    def _update_style(self):
        """Update button style to show current color."""
        r, g, b = self._color
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        text_color = "#333" if brightness > 128 else "#fff"
        self.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); "
            f"color: {text_color}; "
            f"border: 1px solid #555; "
            f"border-radius: 3px; "
            f"font-size: 10px;"
        )
        self.setText(f"#{r:02x}{g:02x}{b:02x}")

    def _pick_color(self):
        """Open color picker dialog."""
        current = QColor(*self._color)
        color = QColorDialog.getColor(current, self, "Select Zone Color")
        if color.isValid():
            self._color = (color.red(), color.green(), color.blue())
            self._update_style()
            self.color_changed.emit(self._color)

    def get_color(self) -> tuple:
        """Get current color as (r, g, b)."""
        return self._color

    def set_color(self, color: tuple):
        """Set the color."""
        self._color = color
        self._update_style()


class ZoneItem(QFrame):
    """A single zone row with name, key count, and color picker."""

    color_changed = Signal(str, tuple)  # Emits (zone_id, (r, g, b))

    def __init__(self, zone: Zone, parent=None):
        super().__init__(parent)
        self.zone = zone
        self._color = (0, 0, 0)
        self._setup_ui()

    def _setup_ui(self):
        """Set up the zone item UI."""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet(
            "QFrame { background-color: #2d2d2d; border-radius: 4px; padding: 4px; }"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)

        # Zone name and description
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        name_label = QLabel(self.zone.name)
        name_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #eee;")
        info_layout.addWidget(name_label)

        key_count = len(self.zone.keys)
        desc = f"{key_count} key{'s' if key_count != 1 else ''}"
        if self.zone.description:
            desc = self.zone.description

        desc_label = QLabel(desc)
        desc_label.setStyleSheet("font-size: 11px; color: #888;")
        info_layout.addWidget(desc_label)

        layout.addLayout(info_layout, 1)

        # Color button
        self.color_btn = ZoneColorButton(self._color)
        self.color_btn.color_changed.connect(self._on_color_changed)
        layout.addWidget(self.color_btn)

    def _on_color_changed(self, color: tuple):
        """Handle color change from button."""
        self._color = color
        self.color_changed.emit(self.zone.id, color)

    def get_color(self) -> tuple:
        """Get current zone color."""
        return self._color

    def set_color(self, color: tuple):
        """Set the zone color."""
        self._color = color
        self.color_btn.set_color(color)


class ZoneEditorWidget(QWidget):
    """Widget for editing zone-based RGB lighting."""

    config_changed = Signal()  # Emits when any zone color changes

    def __init__(self, bridge: OpenRazerBridge, parent=None):
        super().__init__(parent)
        self.bridge = bridge
        self.current_device: RazerDevice | None = None
        self.layout_info: KeyboardLayout | None = None
        self.zone_items: dict[str, ZoneItem] = {}
        self._setup_ui()

    def _setup_ui(self):
        """Set up the widget UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Device info header
        self.device_header = QGroupBox("Matrix Device")
        header_layout = QHBoxLayout(self.device_header)

        self.device_label = QLabel("No device selected")
        self.device_label.setStyleSheet("font-size: 14px;")
        header_layout.addWidget(self.device_label, 1)

        self.matrix_info = QLabel("")
        self.matrix_info.setStyleSheet("color: #888;")
        header_layout.addWidget(self.matrix_info)

        layout.addWidget(self.device_header)

        # Preset selector
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("Quick Preset:"))

        self.preset_combo = QComboBox()
        presets = ["(Select preset)", "Gaming", "Productivity", "Stealth", "Full White"]
        self.preset_combo.addItems(presets)
        self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
        preset_layout.addWidget(self.preset_combo, 1)

        layout.addLayout(preset_layout)

        # Zone list in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        self.zone_container = QWidget()
        self.zone_layout = QVBoxLayout(self.zone_container)
        self.zone_layout.setSpacing(6)
        self.zone_layout.setContentsMargins(0, 0, 0, 0)
        self.zone_layout.addStretch()

        scroll.setWidget(self.zone_container)
        layout.addWidget(scroll, 1)

        # Quick actions
        action_layout = QHBoxLayout()

        self.fill_all_btn = QPushButton("Fill All")
        self.fill_all_btn.clicked.connect(self._fill_all_zones)
        action_layout.addWidget(self.fill_all_btn)

        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.clicked.connect(self._clear_all_zones)
        action_layout.addWidget(self.clear_all_btn)

        action_layout.addStretch()

        self.apply_btn = QPushButton("Apply to Device")
        self.apply_btn.setStyleSheet(
            "QPushButton { background-color: #2a7d2e; padding: 8px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #349639; }"
        )
        self.apply_btn.clicked.connect(self._apply_to_device)
        action_layout.addWidget(self.apply_btn)

        layout.addLayout(action_layout)

        # Initially disabled
        self._set_enabled(False)

    def set_device(self, device: RazerDevice | None):
        """Set the device to edit zones for."""
        self.current_device = device
        self._clear_zone_items()

        if not device or not device.has_matrix:
            self.device_label.setText("No matrix device selected")
            self.matrix_info.setText("")
            self._set_enabled(False)
            return

        # Update header
        self.device_label.setText(device.name)
        self.matrix_info.setText(f"{device.matrix_rows}×{device.matrix_cols} matrix")

        # Get layout for this device
        self.layout_info = get_layout_for_device(
            device.name, device.matrix_rows, device.matrix_cols
        )

        # Create zone items
        for zone in self.layout_info.zones:
            item = ZoneItem(zone)
            item.color_changed.connect(self._on_zone_color_changed)
            self.zone_items[zone.id] = item
            # Insert before the stretch
            self.zone_layout.insertWidget(self.zone_layout.count() - 1, item)

        self._set_enabled(True)

    def _clear_zone_items(self):
        """Remove all zone items."""
        for item in self.zone_items.values():
            item.deleteLater()
        self.zone_items.clear()

    def _set_enabled(self, enabled: bool):
        """Enable or disable controls."""
        self.preset_combo.setEnabled(enabled)
        self.fill_all_btn.setEnabled(enabled)
        self.clear_all_btn.setEnabled(enabled)
        self.apply_btn.setEnabled(enabled)

    def _on_zone_color_changed(self, zone_id: str, color: tuple):
        """Handle zone color change."""
        self.config_changed.emit()

    def _on_preset_changed(self, preset_name: str):
        """Apply a preset to all zones."""
        if preset_name == "(Select preset)":
            return

        preset_key = preset_name.lower().replace(" ", "_")
        colors = get_zones_for_preset(preset_key)

        # Apply preset colors
        for zone_id, color in colors.items():
            if zone_id in self.zone_items:
                self.zone_items[zone_id].set_color(color)

        # Reset combo to placeholder
        self.preset_combo.setCurrentIndex(0)
        self.config_changed.emit()

    def _fill_all_zones(self):
        """Open color picker and fill all zones with that color."""
        color = QColorDialog.getColor(QColor(0, 255, 0), self, "Select Fill Color")
        if color.isValid():
            rgb = (color.red(), color.green(), color.blue())
            for item in self.zone_items.values():
                item.set_color(rgb)
            self.config_changed.emit()

    def _clear_all_zones(self):
        """Set all zones to black (off)."""
        for item in self.zone_items.values():
            item.set_color((0, 0, 0))
        self.config_changed.emit()

    def _apply_to_device(self):
        """Apply current zone colors to the physical device."""
        if not self.current_device or not self.layout_info:
            return

        # Build matrix from zone colors
        rows = self.layout_info.rows
        cols = self.layout_info.cols
        matrix: list[list[tuple[int, int, int]]] = [
            [(0, 0, 0) for _ in range(cols)] for _ in range(rows)
        ]

        # Fill matrix from zone colors
        for zone_id, item in self.zone_items.items():
            zone = self.layout_info.get_zone(zone_id)
            if zone:
                color = item.get_color()
                for key in zone.keys:
                    if 0 <= key.row < rows and 0 <= key.col < cols:
                        matrix[key.row][key.col] = color

        # Send to device
        self.bridge.set_matrix_colors(self.current_device.serial, matrix)

    def get_zone_colors(self) -> dict[str, tuple[int, int, int]]:
        """Get all current zone colors."""
        return {zone_id: item.get_color() for zone_id, item in self.zone_items.items()}

    def set_zone_colors(self, colors: dict[str, tuple[int, int, int]]):
        """Set zone colors from a dict."""
        for zone_id, color in colors.items():
            if zone_id in self.zone_items:
                self.zone_items[zone_id].set_color(color)
