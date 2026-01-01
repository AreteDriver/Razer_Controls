"""Macro editor widget for visual macro creation and editing."""

import uuid

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from crates.keycode_map import get_all_schema_keys
from crates.profile_schema import MacroAction, MacroStep, MacroStepType


class StepEditorDialog(QDialog):
    """Dialog for editing a single macro step."""

    def __init__(self, step: MacroStep | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Macro Step")
        self.setMinimumWidth(350)

        self._step = step
        self._setup_ui()

        if step:
            self._load_step(step)

    def _setup_ui(self):
        layout = QFormLayout(self)

        # Step type
        self.type_combo = QComboBox()
        self.type_combo.addItem("Key Press", MacroStepType.KEY_PRESS)
        self.type_combo.addItem("Key Down", MacroStepType.KEY_DOWN)
        self.type_combo.addItem("Key Up", MacroStepType.KEY_UP)
        self.type_combo.addItem("Delay", MacroStepType.DELAY)
        self.type_combo.addItem("Type Text", MacroStepType.TEXT)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        layout.addRow("Type:", self.type_combo)

        # Key selector (for key actions)
        self.key_combo = QComboBox()
        self.key_combo.setEditable(True)
        for key in sorted(get_all_schema_keys()):
            self.key_combo.addItem(key)
        layout.addRow("Key:", self.key_combo)

        # Delay input (for delay actions)
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 10000)
        self.delay_spin.setValue(100)
        self.delay_spin.setSuffix(" ms")
        layout.addRow("Delay:", self.delay_spin)

        # Text input (for text actions)
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Text to type...")
        layout.addRow("Text:", self.text_input)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self._on_type_changed()

    def _on_type_changed(self):
        """Show/hide fields based on step type."""
        step_type = self.type_combo.currentData()

        is_key = step_type in (
            MacroStepType.KEY_PRESS,
            MacroStepType.KEY_DOWN,
            MacroStepType.KEY_UP,
        )
        is_delay = step_type == MacroStepType.DELAY
        is_text = step_type == MacroStepType.TEXT

        self.key_combo.setVisible(is_key)
        self.delay_spin.setVisible(is_delay)
        self.text_input.setVisible(is_text)

    def _load_step(self, step: MacroStep):
        """Load step data into dialog."""
        # Set type
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == step.type:
                self.type_combo.setCurrentIndex(i)
                break

        if step.key:
            idx = self.key_combo.findText(step.key)
            if idx >= 0:
                self.key_combo.setCurrentIndex(idx)
            else:
                self.key_combo.setEditText(step.key)

        if step.delay_ms:
            self.delay_spin.setValue(step.delay_ms)

        if step.text:
            self.text_input.setText(step.text)

    def get_step(self) -> MacroStep:
        """Get the configured step."""
        step_type = self.type_combo.currentData()

        return MacroStep(
            type=step_type,
            key=self.key_combo.currentText()
            if step_type
            in (
                MacroStepType.KEY_PRESS,
                MacroStepType.KEY_DOWN,
                MacroStepType.KEY_UP,
            )
            else None,
            delay_ms=self.delay_spin.value() if step_type == MacroStepType.DELAY else None,
            text=self.text_input.text() if step_type == MacroStepType.TEXT else None,
        )


class MacroEditorWidget(QWidget):
    """Widget for creating and editing macros."""

    macro_changed = Signal(MacroAction)  # Emitted when macro is modified
    macros_updated = Signal(list)  # Emitted when macro list changes

    def __init__(self, parent=None):
        super().__init__(parent)
        self._macros: list[MacroAction] = []
        self._current_macro: MacroAction | None = None
        self._recording = False

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)

        # Left side - macro list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("Macros:"))

        self.macro_list = QListWidget()
        self.macro_list.currentItemChanged.connect(self._on_macro_selected)
        left_layout.addWidget(self.macro_list)

        # Macro list buttons
        macro_btn_layout = QHBoxLayout()
        self.add_macro_btn = QPushButton("New")
        self.add_macro_btn.clicked.connect(self._add_macro)
        macro_btn_layout.addWidget(self.add_macro_btn)

        self.delete_macro_btn = QPushButton("Delete")
        self.delete_macro_btn.clicked.connect(self._delete_macro)
        self.delete_macro_btn.setEnabled(False)
        macro_btn_layout.addWidget(self.delete_macro_btn)

        left_layout.addLayout(macro_btn_layout)

        # Right side - macro editor
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # Macro properties
        props_group = QGroupBox("Macro Properties")
        props_layout = QFormLayout(props_group)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Macro name...")
        self.name_input.textChanged.connect(self._on_name_changed)
        props_layout.addRow("Name:", self.name_input)

        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 100)
        self.repeat_spin.setValue(1)
        self.repeat_spin.valueChanged.connect(self._on_repeat_changed)
        props_layout.addRow("Repeat:", self.repeat_spin)

        self.repeat_delay_spin = QSpinBox()
        self.repeat_delay_spin.setRange(0, 5000)
        self.repeat_delay_spin.setValue(0)
        self.repeat_delay_spin.setSuffix(" ms")
        self.repeat_delay_spin.valueChanged.connect(self._on_repeat_delay_changed)
        props_layout.addRow("Repeat Delay:", self.repeat_delay_spin)

        right_layout.addWidget(props_group)

        # Steps editor
        steps_group = QGroupBox("Steps")
        steps_layout = QVBoxLayout(steps_group)

        self.steps_list = QListWidget()
        self.steps_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.steps_list.model().rowsMoved.connect(self._on_steps_reordered)
        steps_layout.addWidget(self.steps_list)

        # Step buttons
        step_btn_layout = QHBoxLayout()

        self.add_step_btn = QPushButton("Add Step")
        self.add_step_btn.clicked.connect(self._add_step)
        step_btn_layout.addWidget(self.add_step_btn)

        self.edit_step_btn = QPushButton("Edit")
        self.edit_step_btn.clicked.connect(self._edit_step)
        self.edit_step_btn.setEnabled(False)
        step_btn_layout.addWidget(self.edit_step_btn)

        self.delete_step_btn = QPushButton("Delete")
        self.delete_step_btn.clicked.connect(self._delete_step)
        self.delete_step_btn.setEnabled(False)
        step_btn_layout.addWidget(self.delete_step_btn)

        steps_layout.addLayout(step_btn_layout)

        # Record button
        record_layout = QHBoxLayout()
        self.record_btn = QPushButton("Record from Device")
        self.record_btn.setCheckable(True)
        self.record_btn.clicked.connect(self._toggle_recording)
        record_layout.addWidget(self.record_btn)

        self.record_status = QLabel()
        record_layout.addWidget(self.record_status)
        record_layout.addStretch()

        steps_layout.addLayout(record_layout)

        right_layout.addWidget(steps_group)

        # Test button
        test_layout = QHBoxLayout()
        self.test_btn = QPushButton("Test Macro")
        self.test_btn.clicked.connect(self._test_macro)
        self.test_btn.setEnabled(False)
        test_layout.addWidget(self.test_btn)
        test_layout.addStretch()
        right_layout.addLayout(test_layout)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 400])

        layout.addWidget(splitter)

        # Connect step selection
        self.steps_list.currentItemChanged.connect(self._on_step_selected)
        self.steps_list.itemDoubleClicked.connect(self._edit_step)

        # Disable editor initially
        self._set_editor_enabled(False)

    def set_macros(self, macros: list[MacroAction]):
        """Set the list of macros to edit."""
        self._macros = macros
        self._refresh_macro_list()

    def get_macros(self) -> list[MacroAction]:
        """Get the current macro list."""
        return self._macros

    def _refresh_macro_list(self):
        """Refresh the macro list widget."""
        self.macro_list.clear()
        for macro in self._macros:
            item = QListWidgetItem(macro.name)
            item.setData(Qt.ItemDataRole.UserRole, macro.id)
            self.macro_list.addItem(item)

    def _on_macro_selected(self, current, previous):
        """Handle macro selection change."""
        if current:
            macro_id = current.data(Qt.ItemDataRole.UserRole)
            self._current_macro = next((m for m in self._macros if m.id == macro_id), None)
            self._load_macro(self._current_macro)
            self._set_editor_enabled(True)
            self.delete_macro_btn.setEnabled(True)
        else:
            self._current_macro = None
            self._set_editor_enabled(False)
            self.delete_macro_btn.setEnabled(False)

    def _load_macro(self, macro: MacroAction | None):
        """Load macro data into editor."""
        if not macro:
            return

        self.name_input.blockSignals(True)
        self.name_input.setText(macro.name)
        self.name_input.blockSignals(False)

        self.repeat_spin.blockSignals(True)
        self.repeat_spin.setValue(macro.repeat_count)
        self.repeat_spin.blockSignals(False)

        self.repeat_delay_spin.blockSignals(True)
        self.repeat_delay_spin.setValue(macro.repeat_delay_ms)
        self.repeat_delay_spin.blockSignals(False)

        self._refresh_steps_list()
        self.test_btn.setEnabled(len(macro.steps) > 0)

    def _refresh_steps_list(self):
        """Refresh the steps list widget."""
        self.steps_list.clear()
        if not self._current_macro:
            return

        for i, step in enumerate(self._current_macro.steps):
            text = self._step_to_text(step)
            item = QListWidgetItem(f"{i + 1}. {text}")
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.steps_list.addItem(item)

    def _step_to_text(self, step: MacroStep) -> str:
        """Convert step to display text."""
        if step.type == MacroStepType.KEY_PRESS:
            return f"Press {step.key}"
        elif step.type == MacroStepType.KEY_DOWN:
            return f"Hold {step.key}"
        elif step.type == MacroStepType.KEY_UP:
            return f"Release {step.key}"
        elif step.type == MacroStepType.DELAY:
            return f"Wait {step.delay_ms}ms"
        elif step.type == MacroStepType.TEXT:
            return f'Type "{step.text}"'
        return str(step.type)

    def _set_editor_enabled(self, enabled: bool):
        """Enable/disable the editor panel."""
        self.name_input.setEnabled(enabled)
        self.repeat_spin.setEnabled(enabled)
        self.repeat_delay_spin.setEnabled(enabled)
        self.steps_list.setEnabled(enabled)
        self.add_step_btn.setEnabled(enabled)
        self.record_btn.setEnabled(enabled)

    def _on_step_selected(self, current, previous):
        """Handle step selection change."""
        has_selection = current is not None
        self.edit_step_btn.setEnabled(has_selection)
        self.delete_step_btn.setEnabled(has_selection)

    def _add_macro(self):
        """Add a new macro."""
        macro = MacroAction(
            id=str(uuid.uuid4())[:8],
            name=f"Macro {len(self._macros) + 1}",
            steps=[],
        )
        self._macros.append(macro)
        self._refresh_macro_list()

        # Select the new macro
        self.macro_list.setCurrentRow(len(self._macros) - 1)
        self.macros_updated.emit(self._macros)

    def _delete_macro(self):
        """Delete the selected macro."""
        if not self._current_macro:
            return

        confirm = QMessageBox.question(
            self,
            "Delete Macro",
            f"Delete macro '{self._current_macro.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if confirm == QMessageBox.StandardButton.Yes:
            self._macros = [m for m in self._macros if m.id != self._current_macro.id]
            self._current_macro = None
            self._refresh_macro_list()
            self.macros_updated.emit(self._macros)

    def _add_step(self):
        """Add a new step to the current macro."""
        if not self._current_macro:
            return

        dialog = StepEditorDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            step = dialog.get_step()
            self._current_macro.steps.append(step)
            self._refresh_steps_list()
            self._emit_macro_changed()
            self.test_btn.setEnabled(True)

    def _edit_step(self):
        """Edit the selected step."""
        if not self._current_macro:
            return

        current = self.steps_list.currentItem()
        if not current:
            return

        idx = current.data(Qt.ItemDataRole.UserRole)
        step = self._current_macro.steps[idx]

        dialog = StepEditorDialog(step, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._current_macro.steps[idx] = dialog.get_step()
            self._refresh_steps_list()
            self._emit_macro_changed()

    def _delete_step(self):
        """Delete the selected step."""
        if not self._current_macro:
            return

        current = self.steps_list.currentItem()
        if not current:
            return

        idx = current.data(Qt.ItemDataRole.UserRole)
        del self._current_macro.steps[idx]
        self._refresh_steps_list()
        self._emit_macro_changed()
        self.test_btn.setEnabled(len(self._current_macro.steps) > 0)

    def _on_steps_reordered(self):
        """Handle steps being reordered via drag-drop."""
        if not self._current_macro:
            return

        # Rebuild steps list from widget order
        new_steps = []
        for i in range(self.steps_list.count()):
            item = self.steps_list.item(i)
            old_idx = item.data(Qt.ItemDataRole.UserRole)
            new_steps.append(self._current_macro.steps[old_idx])

        self._current_macro.steps = new_steps
        self._refresh_steps_list()
        self._emit_macro_changed()

    def _on_name_changed(self, text: str):
        """Handle macro name change."""
        if self._current_macro:
            self._current_macro.name = text
            # Update list item
            current = self.macro_list.currentItem()
            if current:
                current.setText(text)
            self._emit_macro_changed()

    def _on_repeat_changed(self, value: int):
        """Handle repeat count change."""
        if self._current_macro:
            self._current_macro.repeat_count = value
            self._emit_macro_changed()

    def _on_repeat_delay_changed(self, value: int):
        """Handle repeat delay change."""
        if self._current_macro:
            self._current_macro.repeat_delay_ms = value
            self._emit_macro_changed()

    def _emit_macro_changed(self):
        """Emit signal that macro was modified."""
        if self._current_macro:
            self.macro_changed.emit(self._current_macro)
            self.macros_updated.emit(self._macros)

    def _toggle_recording(self):
        """Toggle macro recording mode."""
        if self._recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Start recording macro from device input."""
        if not self._current_macro:
            return

        self._recording = True
        self.record_btn.setText("Stop Recording")
        self.record_status.setText("Recording... Press keys on your device")
        self.record_status.setStyleSheet("color: red; font-weight: bold;")

        # Note: Actual device recording would require evdev access
        # For now, show a message about the limitation
        QMessageBox.information(
            self,
            "Recording",
            "Device recording requires running the daemon with elevated privileges.\n\n"
            "For now, use 'Add Step' to manually add macro steps, or use the CLI:\n"
            "  razer-macro record --device /dev/input/eventX",
        )
        self._stop_recording()

    def _stop_recording(self):
        """Stop recording."""
        self._recording = False
        self.record_btn.setText("Record from Device")
        self.record_btn.setChecked(False)
        self.record_status.setText("")
        self.record_status.setStyleSheet("")

    def _test_macro(self):
        """Test the current macro."""
        if not self._current_macro or not self._current_macro.steps:
            return

        # Show what would be played
        steps_text = "\n".join(
            f"  {i + 1}. {self._step_to_text(s)}" for i, s in enumerate(self._current_macro.steps)
        )

        QMessageBox.information(
            self,
            "Test Macro",
            f"Macro '{self._current_macro.name}' would execute:\n\n"
            f"{steps_text}\n\n"
            f"Repeat: {self._current_macro.repeat_count}x\n"
            f"Delay between repeats: {self._current_macro.repeat_delay_ms}ms\n\n"
            "Note: Actual playback requires the remap daemon running.",
        )
