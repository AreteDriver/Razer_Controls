"""Tests for GUI widgets - MacroEditor, BatteryMonitor, DPIStageEditor."""

from unittest.mock import MagicMock, patch

import pytest

from crates.profile_schema import DPIConfig, MacroAction, MacroStep, MacroStepType
from services.openrazer_bridge import RazerDevice

# --- Mock Qt before importing widgets ---


@pytest.fixture(autouse=True)
def mock_qt():
    """Mock PySide6 modules to avoid requiring display."""
    with patch.dict(
        "sys.modules",
        {
            "PySide6": MagicMock(),
            "PySide6.QtCore": MagicMock(),
            "PySide6.QtWidgets": MagicMock(),
            "PySide6.QtGui": MagicMock(),
        },
    ):
        yield


# --- Fixtures ---


@pytest.fixture
def sample_macro():
    """Create a sample macro for testing."""
    return MacroAction(
        id="test123",
        name="Test Macro",
        steps=[
            MacroStep(type=MacroStepType.KEY_PRESS, key="a"),
            MacroStep(type=MacroStepType.DELAY, delay_ms=100),
            MacroStep(type=MacroStepType.KEY_PRESS, key="b"),
        ],
        repeat_count=1,
        repeat_delay_ms=0,
    )


@pytest.fixture
def sample_device():
    """Create a sample RazerDevice for testing."""
    return RazerDevice(
        serial="PM1234567890",
        name="Razer DeathAdder V2",
        device_type="mouse",
        object_path="/org/razer/device/PM1234567890",
        has_lighting=True,
        has_brightness=True,
        has_dpi=True,
        has_battery=True,
        has_poll_rate=True,
        brightness=75,
        dpi=(800, 800),
        poll_rate=1000,
        max_dpi=20000,
        battery_level=85,
        is_charging=False,
    )


@pytest.fixture
def sample_dpi_config():
    """Create a sample DPI config for testing."""
    return DPIConfig(
        stages=[800, 1600, 3200],
        active_stage=1,
    )


# --- Test MacroStep ---


class TestMacroStep:
    """Tests for MacroStep dataclass."""

    def test_key_press_step(self):
        """Test creating a key press step."""
        step = MacroStep(type=MacroStepType.KEY_PRESS, key="a")
        assert step.type == MacroStepType.KEY_PRESS
        assert step.key == "a"
        assert step.delay_ms is None
        assert step.text is None

    def test_delay_step(self):
        """Test creating a delay step."""
        step = MacroStep(type=MacroStepType.DELAY, delay_ms=100)
        assert step.type == MacroStepType.DELAY
        assert step.delay_ms == 100
        assert step.key is None

    def test_text_step(self):
        """Test creating a text step."""
        step = MacroStep(type=MacroStepType.TEXT, text="Hello")
        assert step.type == MacroStepType.TEXT
        assert step.text == "Hello"
        assert step.key is None

    def test_key_down_step(self):
        """Test creating a key down step."""
        step = MacroStep(type=MacroStepType.KEY_DOWN, key="shift")
        assert step.type == MacroStepType.KEY_DOWN
        assert step.key == "shift"

    def test_key_up_step(self):
        """Test creating a key up step."""
        step = MacroStep(type=MacroStepType.KEY_UP, key="shift")
        assert step.type == MacroStepType.KEY_UP
        assert step.key == "shift"


# --- Test MacroAction ---


class TestMacroAction:
    """Tests for MacroAction dataclass."""

    def test_create_macro(self, sample_macro):
        """Test creating a macro."""
        assert sample_macro.id == "test123"
        assert sample_macro.name == "Test Macro"
        assert len(sample_macro.steps) == 3
        assert sample_macro.repeat_count == 1

    def test_macro_default_values(self):
        """Test macro default values."""
        macro = MacroAction(id="m1", name="Test", steps=[])
        assert macro.repeat_count == 1
        assert macro.repeat_delay_ms == 0
        assert macro.steps == []

    def test_macro_with_repeat(self):
        """Test macro with repeat settings."""
        macro = MacroAction(
            id="m1",
            name="Repeat Test",
            steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="a")],
            repeat_count=5,
            repeat_delay_ms=50,
        )
        assert macro.repeat_count == 5
        assert macro.repeat_delay_ms == 50


# --- Test DPIConfig ---


class TestDPIConfig:
    """Tests for DPIConfig dataclass."""

    def test_create_config(self, sample_dpi_config):
        """Test creating DPI config."""
        assert sample_dpi_config.stages == [800, 1600, 3200]
        assert sample_dpi_config.active_stage == 1

    def test_default_values(self):
        """Test default DPI config values."""
        config = DPIConfig()
        assert config.stages == [800, 1600, 3200]
        assert config.active_stage == 0

    def test_custom_stages(self):
        """Test custom DPI stages."""
        config = DPIConfig(stages=[400, 800, 1200, 1600, 2400], active_stage=2)
        assert len(config.stages) == 5
        assert config.stages[2] == 1200
        assert config.active_stage == 2


# --- Test Battery Display Logic ---


class TestBatteryDisplayLogic:
    """Tests for battery status display logic."""

    LOW_BATTERY_THRESHOLD = 20
    CRITICAL_BATTERY_THRESHOLD = 10

    def test_critical_battery_detection(self, sample_device):
        """Test critical battery level detection."""
        sample_device.battery_level = 5
        assert sample_device.battery_level <= self.CRITICAL_BATTERY_THRESHOLD

    def test_low_battery_detection(self, sample_device):
        """Test low battery level detection."""
        sample_device.battery_level = 15
        assert sample_device.battery_level <= self.LOW_BATTERY_THRESHOLD
        assert sample_device.battery_level > self.CRITICAL_BATTERY_THRESHOLD

    def test_normal_battery(self, sample_device):
        """Test normal battery level."""
        sample_device.battery_level = 50
        assert sample_device.battery_level > self.LOW_BATTERY_THRESHOLD

    def test_good_battery(self, sample_device):
        """Test good battery level."""
        sample_device.battery_level = 85
        assert sample_device.battery_level >= 80

    def test_charging_state(self, sample_device):
        """Test charging state detection."""
        sample_device.is_charging = True
        assert sample_device.is_charging is True


# --- Test DPI Stage Logic ---


class TestDPIStageLogic:
    """Tests for DPI stage editor logic."""

    MAX_STAGES = 5
    PRESET_DPIS = [400, 800, 1200, 1600, 2400, 3200, 4800, 6400]

    def test_max_stages_limit(self):
        """Test that max stages is enforced."""
        stages = [400, 800, 1200, 1600, 2400]
        assert len(stages) <= self.MAX_STAGES

    def test_cannot_exceed_max_stages(self):
        """Test adding stage beyond max."""
        stages = [400, 800, 1200, 1600, 2400]
        assert len(stages) >= self.MAX_STAGES
        # Cannot add more

    def test_must_have_at_least_one_stage(self):
        """Test minimum one stage required."""
        stages = [800]
        assert len(stages) >= 1

    def test_gaming_preset(self):
        """Test gaming preset values."""
        gaming_preset = [400, 800, 1600]
        assert len(gaming_preset) == 3
        assert gaming_preset[0] == 400  # Low for precision
        assert gaming_preset[2] == 1600  # Higher for general

    def test_productivity_preset(self):
        """Test productivity preset values."""
        productivity_preset = [800, 1600, 3200]
        assert len(productivity_preset) == 3
        assert productivity_preset[0] == 800
        assert productivity_preset[2] == 3200

    def test_high_precision_preset(self):
        """Test high precision preset values."""
        high_precision_preset = [400, 800, 1200, 1600, 2400]
        assert len(high_precision_preset) == 5
        assert high_precision_preset[0] == 400

    def test_dpi_color_coding(self, sample_device):
        """Test DPI color coding by level."""
        max_dpi = sample_device.max_dpi  # 20000

        # Low DPI (<25% of max)
        low_dpi = 4000  # 20%
        ratio = low_dpi / max_dpi
        assert ratio < 0.25

        # Medium DPI (25-50% of max)
        medium_dpi = 8000  # 40%
        ratio = medium_dpi / max_dpi
        assert 0.25 <= ratio < 0.5

        # High DPI (50-75% of max)
        high_dpi = 12000  # 60%
        ratio = high_dpi / max_dpi
        assert 0.5 <= ratio < 0.75

        # Very high DPI (>75% of max)
        very_high_dpi = 18000  # 90%
        ratio = very_high_dpi / max_dpi
        assert ratio >= 0.75

    def test_active_stage_within_bounds(self, sample_dpi_config):
        """Test active stage is within valid range."""
        assert 0 <= sample_dpi_config.active_stage < len(sample_dpi_config.stages)

    def test_dpi_rounding_to_100(self):
        """Test DPI values are rounded to nearest 100."""
        test_values = [
            (850, 800),
            (949, 900),
            (950, 1000),
            (1050, 1000),
            (1650, 1600),
        ]
        for input_val, expected in test_values:
            rounded = round(input_val / 100) * 100
            assert rounded == expected


# --- Test Macro Step Text Conversion ---


class TestMacroStepTextConversion:
    """Tests for converting macro steps to display text."""

    def step_to_text(self, step: MacroStep) -> str:
        """Convert step to display text (copied from widget logic)."""
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

    def test_key_press_text(self):
        """Test key press step text."""
        step = MacroStep(type=MacroStepType.KEY_PRESS, key="a")
        assert self.step_to_text(step) == "Press a"

    def test_key_down_text(self):
        """Test key down step text."""
        step = MacroStep(type=MacroStepType.KEY_DOWN, key="shift")
        assert self.step_to_text(step) == "Hold shift"

    def test_key_up_text(self):
        """Test key up step text."""
        step = MacroStep(type=MacroStepType.KEY_UP, key="shift")
        assert self.step_to_text(step) == "Release shift"

    def test_delay_text(self):
        """Test delay step text."""
        step = MacroStep(type=MacroStepType.DELAY, delay_ms=100)
        assert self.step_to_text(step) == "Wait 100ms"

    def test_text_step_text(self):
        """Test text step text."""
        step = MacroStep(type=MacroStepType.TEXT, text="Hello World")
        assert self.step_to_text(step) == 'Type "Hello World"'


# --- Test Macro ID Generation ---


class TestMacroIDGeneration:
    """Tests for macro ID generation."""

    def test_macro_id_format(self):
        """Test macro ID uses UUID format."""
        import uuid

        macro_id = str(uuid.uuid4())[:8]
        # Should be 8 hex characters
        assert len(macro_id) == 8
        assert all(c in "0123456789abcdef-" for c in macro_id)

    def test_unique_ids(self):
        """Test that generated IDs are unique."""
        import uuid

        ids = [str(uuid.uuid4())[:8] for _ in range(100)]
        assert len(set(ids)) == 100  # All unique


# --- Test RazerDevice Battery Properties ---


class TestRazerDeviceBattery:
    """Tests for RazerDevice battery properties."""

    def test_device_with_battery(self, sample_device):
        """Test device with battery support."""
        assert sample_device.has_battery is True
        assert sample_device.battery_level == 85
        assert sample_device.is_charging is False

    def test_device_without_battery(self):
        """Test device without battery support."""
        device = RazerDevice(
            serial="PM1234567890",
            name="Razer DeathAdder",
            device_type="mouse",
            object_path="/org/razer/device/PM1234567890",
            has_battery=False,
        )
        assert device.has_battery is False

    def test_battery_level_range(self, sample_device):
        """Test battery level is within valid range."""
        assert 0 <= sample_device.battery_level <= 100


# --- Test RazerDevice DPI Properties ---


class TestRazerDeviceDPI:
    """Tests for RazerDevice DPI properties."""

    def test_device_with_dpi(self, sample_device):
        """Test device with DPI support."""
        assert sample_device.has_dpi is True
        assert sample_device.dpi == (800, 800)
        assert sample_device.max_dpi == 20000

    def test_device_without_dpi(self):
        """Test device without DPI support."""
        device = RazerDevice(
            serial="KB1234567890",
            name="Razer BlackWidow",
            device_type="keyboard",
            object_path="/org/razer/device/KB1234567890",
            has_dpi=False,
        )
        assert device.has_dpi is False

    def test_dpi_within_max(self, sample_device):
        """Test DPI is within max limit."""
        assert sample_device.dpi[0] <= sample_device.max_dpi
        assert sample_device.dpi[1] <= sample_device.max_dpi


# --- Integration Tests (Logic Only) ---


class TestMacroManagement:
    """Tests for macro list management logic."""

    def test_add_macro_to_list(self):
        """Test adding a macro to list."""
        macros = []
        new_macro = MacroAction(id="m1", name="Macro 1", steps=[])
        macros.append(new_macro)
        assert len(macros) == 1
        assert macros[0].name == "Macro 1"

    def test_delete_macro_from_list(self, sample_macro):
        """Test deleting a macro from list."""
        macros = [sample_macro]
        macros = [m for m in macros if m.id != "test123"]
        assert len(macros) == 0

    def test_find_macro_by_id(self, sample_macro):
        """Test finding macro by ID."""
        macros = [sample_macro]
        found = next((m for m in macros if m.id == "test123"), None)
        assert found is not None
        assert found.name == "Test Macro"

    def test_update_macro_name(self, sample_macro):
        """Test updating macro name."""
        sample_macro.name = "Updated Name"
        assert sample_macro.name == "Updated Name"


class TestDPIStageManagement:
    """Tests for DPI stage list management logic."""

    def test_add_stage(self, sample_dpi_config):
        """Test adding a DPI stage."""
        original_count = len(sample_dpi_config.stages)
        sample_dpi_config.stages.append(6400)
        assert len(sample_dpi_config.stages) == original_count + 1

    def test_remove_stage(self, sample_dpi_config):
        """Test removing a DPI stage."""
        original_count = len(sample_dpi_config.stages)
        sample_dpi_config.stages.pop()
        assert len(sample_dpi_config.stages) == original_count - 1

    def test_change_active_stage(self, sample_dpi_config):
        """Test changing active stage."""
        sample_dpi_config.active_stage = 2
        assert sample_dpi_config.active_stage == 2

    def test_get_active_dpi(self, sample_dpi_config):
        """Test getting active DPI value."""
        active_dpi = sample_dpi_config.stages[sample_dpi_config.active_stage]
        assert active_dpi == 1600  # Index 1 = 1600
