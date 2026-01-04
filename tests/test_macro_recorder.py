"""Tests for MacroRecorder - macro event recording."""

import time
from unittest.mock import MagicMock, patch

import pytest
from evdev import InputEvent, ecodes

from crates.profile_schema import MacroStepType
from services.macro_engine.recorder import (
    DeviceMacroRecorder,
    MacroRecorder,
    RecordedEvent,
)

# --- Fixtures ---


def make_key_event(code: int, value: int, timestamp: float = 0) -> InputEvent:
    """Create a key event."""
    event = InputEvent(int(timestamp), int((timestamp % 1) * 1000000), ecodes.EV_KEY, code, value)
    return event


@pytest.fixture
def recorder():
    """Create a default MacroRecorder."""
    return MacroRecorder()


@pytest.fixture
def recorder_no_merge():
    """Create a recorder that doesn't merge press+release."""
    return MacroRecorder(merge_press_release=False)


@pytest.fixture
def recorder_no_delays():
    """Create a recorder that doesn't record delays."""
    return MacroRecorder(record_delays=False)


# --- Test Classes ---


class TestRecordedEvent:
    """Tests for RecordedEvent dataclass."""

    def test_create_event(self):
        """Test creating a recorded event."""
        event = RecordedEvent(
            timestamp=1.0,
            code=ecodes.KEY_A,
            value=1,
            key_name="A",
        )
        assert event.timestamp == 1.0
        assert event.code == ecodes.KEY_A
        assert event.value == 1
        assert event.key_name == "A"


class TestMacroRecorderInit:
    """Tests for MacroRecorder initialization."""

    def test_default_init(self, recorder):
        """Test default initialization."""
        assert recorder.min_delay_ms == 10
        assert recorder.max_delay_ms == 5000
        assert recorder.record_delays is True
        assert recorder.merge_press_release is True
        assert recorder.is_recording() is False

    def test_custom_init(self):
        """Test custom initialization."""
        recorder = MacroRecorder(
            min_delay_ms=50,
            max_delay_ms=2000,
            record_delays=False,
            merge_press_release=False,
        )
        assert recorder.min_delay_ms == 50
        assert recorder.max_delay_ms == 2000
        assert recorder.record_delays is False
        assert recorder.merge_press_release is False


class TestRecordingState:
    """Tests for recording state management."""

    def test_start_sets_recording(self, recorder):
        """Test start sets recording state."""
        recorder.start()
        assert recorder.is_recording() is True

    def test_stop_clears_recording(self, recorder):
        """Test stop clears recording state."""
        recorder.start()
        recorder.stop()
        assert recorder.is_recording() is False

    def test_start_clears_previous_events(self, recorder):
        """Test start clears events from previous recording."""
        recorder.start()
        recorder.record_event(make_key_event(ecodes.KEY_A, 1))
        assert recorder.get_event_count() == 1

        recorder.start()
        assert recorder.get_event_count() == 0


class TestRecordEvent:
    """Tests for event recording."""

    def test_record_key_down(self, recorder):
        """Test recording key down event."""
        recorder.start()
        result = recorder.record_event(make_key_event(ecodes.KEY_A, 1))

        assert result is True
        assert recorder.get_event_count() == 1

    def test_record_key_up(self, recorder):
        """Test recording key up event."""
        recorder.start()
        result = recorder.record_event(make_key_event(ecodes.KEY_A, 0))

        assert result is True
        assert recorder.get_event_count() == 1

    def test_ignore_repeat_events(self, recorder):
        """Test repeat events (value=2) are ignored."""
        recorder.start()
        result = recorder.record_event(make_key_event(ecodes.KEY_A, 2))

        assert result is False
        assert recorder.get_event_count() == 0

    def test_ignore_non_key_events(self, recorder):
        """Test non-key events are ignored."""
        recorder.start()
        event = InputEvent(0, 0, ecodes.EV_REL, ecodes.REL_X, 10)
        result = recorder.record_event(event)

        assert result is False
        assert recorder.get_event_count() == 0

    def test_ignore_when_not_recording(self, recorder):
        """Test events ignored when not recording."""
        result = recorder.record_event(make_key_event(ecodes.KEY_A, 1))

        assert result is False
        assert recorder.get_event_count() == 0

    def test_record_mouse_button(self, recorder):
        """Test recording mouse button events."""
        recorder.start()
        result = recorder.record_event(make_key_event(ecodes.BTN_LEFT, 1))

        assert result is True
        assert recorder.get_event_count() == 1


class TestEventCallback:
    """Tests for event callback."""

    def test_callback_called_on_record(self, recorder):
        """Test callback is called when event is recorded."""
        callback = MagicMock()
        recorder.set_event_callback(callback)

        recorder.start()
        recorder.record_event(make_key_event(ecodes.KEY_A, 1))

        assert callback.call_count == 1
        recorded_event = callback.call_args[0][0]
        assert recorded_event.key_name == "A"
        assert recorded_event.value == 1


class TestClear:
    """Tests for clear method."""

    def test_clear_removes_events(self, recorder):
        """Test clear removes recorded events."""
        recorder.start()
        recorder.record_event(make_key_event(ecodes.KEY_A, 1))
        recorder.record_event(make_key_event(ecodes.KEY_A, 0))
        assert recorder.get_event_count() == 2

        recorder.clear()
        assert recorder.get_event_count() == 0

    def test_clear_keeps_recording(self, recorder):
        """Test clear doesn't stop recording."""
        recorder.start()
        recorder.clear()
        assert recorder.is_recording() is True


class TestBuildMacro:
    """Tests for macro building."""

    def test_empty_macro(self, recorder):
        """Test building macro with no events."""
        recorder.start()
        macro = recorder.stop()

        assert macro.id == "recorded_macro"
        assert macro.name == "Recorded Macro"
        assert len(macro.steps) == 0

    def test_single_key_press(self, recorder):
        """Test quick press+release merged into KEY_PRESS."""
        recorder.start()
        # Simulate quick press and release
        recorder._events = [
            RecordedEvent(timestamp=1.0, code=ecodes.KEY_A, value=1, key_name="A"),
            RecordedEvent(timestamp=1.05, code=ecodes.KEY_A, value=0, key_name="A"),
        ]
        macro = recorder.stop()

        assert len(macro.steps) == 1
        assert macro.steps[0].type == MacroStepType.KEY_PRESS
        assert macro.steps[0].key == "A"

    def test_no_merge_separate_down_up(self, recorder_no_merge):
        """Test without merge, down and up are separate."""
        recorder_no_merge.start()
        recorder_no_merge._events = [
            RecordedEvent(timestamp=1.0, code=ecodes.KEY_A, value=1, key_name="A"),
            RecordedEvent(timestamp=1.05, code=ecodes.KEY_A, value=0, key_name="A"),
        ]
        macro = recorder_no_merge.stop()

        # DOWN, DELAY (50ms), UP
        key_steps = [s for s in macro.steps if s.type != MacroStepType.DELAY]
        assert len(key_steps) == 2
        assert key_steps[0].type == MacroStepType.KEY_DOWN
        assert key_steps[1].type == MacroStepType.KEY_UP

    def test_held_key_not_merged(self, recorder):
        """Test held key (>100ms) is not merged."""
        recorder.start()
        recorder._events = [
            RecordedEvent(timestamp=1.0, code=ecodes.KEY_A, value=1, key_name="A"),
            RecordedEvent(timestamp=1.2, code=ecodes.KEY_A, value=0, key_name="A"),  # 200ms later
        ]
        macro = recorder.stop()

        assert len(macro.steps) == 3  # DOWN, DELAY, UP
        assert macro.steps[0].type == MacroStepType.KEY_DOWN
        assert macro.steps[1].type == MacroStepType.DELAY
        assert macro.steps[2].type == MacroStepType.KEY_UP

    def test_delay_between_keys(self, recorder):
        """Test delays are recorded between keys."""
        recorder.start()
        recorder._events = [
            RecordedEvent(timestamp=1.0, code=ecodes.KEY_A, value=1, key_name="A"),
            RecordedEvent(timestamp=1.05, code=ecodes.KEY_A, value=0, key_name="A"),
            RecordedEvent(timestamp=1.5, code=ecodes.KEY_B, value=1, key_name="B"),  # 450ms delay
            RecordedEvent(timestamp=1.55, code=ecodes.KEY_B, value=0, key_name="B"),
        ]
        macro = recorder.stop()

        # Should be: KEY_PRESS A, DELAY, KEY_PRESS B
        assert len(macro.steps) == 3
        assert macro.steps[0].type == MacroStepType.KEY_PRESS
        assert macro.steps[1].type == MacroStepType.DELAY
        assert macro.steps[1].delay_ms >= 400  # ~450ms
        assert macro.steps[2].type == MacroStepType.KEY_PRESS

    def test_no_delays_recorded(self, recorder_no_delays):
        """Test delays not recorded when disabled."""
        recorder_no_delays.start()
        recorder_no_delays._events = [
            RecordedEvent(timestamp=1.0, code=ecodes.KEY_A, value=1, key_name="A"),
            RecordedEvent(timestamp=1.05, code=ecodes.KEY_A, value=0, key_name="A"),
            RecordedEvent(timestamp=1.5, code=ecodes.KEY_B, value=1, key_name="B"),
            RecordedEvent(timestamp=1.55, code=ecodes.KEY_B, value=0, key_name="B"),
        ]
        macro = recorder_no_delays.stop()

        # Should be: KEY_PRESS A, KEY_PRESS B (no delay)
        assert len(macro.steps) == 2
        assert macro.steps[0].type == MacroStepType.KEY_PRESS
        assert macro.steps[1].type == MacroStepType.KEY_PRESS

    def test_min_delay_threshold(self):
        """Test delays below min_delay_ms are ignored."""
        recorder = MacroRecorder(min_delay_ms=100)
        recorder.start()
        recorder._events = [
            RecordedEvent(timestamp=1.0, code=ecodes.KEY_A, value=1, key_name="A"),
            RecordedEvent(timestamp=1.05, code=ecodes.KEY_A, value=0, key_name="A"),
            RecordedEvent(timestamp=1.08, code=ecodes.KEY_B, value=1, key_name="B"),  # 30ms < 100ms
            RecordedEvent(timestamp=1.13, code=ecodes.KEY_B, value=0, key_name="B"),
        ]
        macro = recorder.stop()

        # No delay step since 30ms < 100ms threshold
        delay_steps = [s for s in macro.steps if s.type == MacroStepType.DELAY]
        assert len(delay_steps) == 0

    def test_max_delay_cap(self):
        """Test delays are capped at max_delay_ms."""
        recorder = MacroRecorder(max_delay_ms=1000)
        recorder.start()
        recorder._events = [
            RecordedEvent(timestamp=1.0, code=ecodes.KEY_A, value=1, key_name="A"),
            RecordedEvent(timestamp=1.05, code=ecodes.KEY_A, value=0, key_name="A"),
            RecordedEvent(timestamp=4.0, code=ecodes.KEY_B, value=1, key_name="B"),  # 2950ms
            RecordedEvent(timestamp=4.05, code=ecodes.KEY_B, value=0, key_name="B"),
        ]
        macro = recorder.stop()

        delay_steps = [s for s in macro.steps if s.type == MacroStepType.DELAY]
        assert len(delay_steps) == 1
        assert delay_steps[0].delay_ms == 1000  # Capped


class TestChordRecording:
    """Tests for recording key chords."""

    def test_chord_with_modifier(self, recorder):
        """Test recording Ctrl+C chord."""
        recorder.start()
        recorder._events = [
            RecordedEvent(timestamp=1.0, code=ecodes.KEY_LEFTCTRL, value=1, key_name="CTRL"),
            RecordedEvent(timestamp=1.1, code=ecodes.KEY_C, value=1, key_name="C"),
            RecordedEvent(timestamp=1.15, code=ecodes.KEY_C, value=0, key_name="C"),
            RecordedEvent(timestamp=1.2, code=ecodes.KEY_LEFTCTRL, value=0, key_name="CTRL"),
        ]
        macro = recorder.stop()

        # CTRL down, delay, C press, delay, CTRL up
        down_steps = [s for s in macro.steps if s.type == MacroStepType.KEY_DOWN]
        up_steps = [s for s in macro.steps if s.type == MacroStepType.KEY_UP]
        press_steps = [s for s in macro.steps if s.type == MacroStepType.KEY_PRESS]

        assert len(down_steps) == 1  # CTRL down
        assert len(up_steps) == 1  # CTRL up
        assert len(press_steps) == 1  # C press (merged)


class TestDeviceMacroRecorder:
    """Tests for DeviceMacroRecorder."""

    def test_init(self):
        """Test DeviceMacroRecorder initialization."""
        recorder = DeviceMacroRecorder("/dev/input/event0", stop_key="F12")

        assert recorder.device_path == "/dev/input/event0"
        assert recorder.stop_key == "F12"

    def test_stop_key_uppercase(self):
        """Test stop key is uppercased."""
        recorder = DeviceMacroRecorder("/dev/input/event0", stop_key="esc")
        assert recorder.stop_key == "ESC"

    @patch("services.macro_engine.recorder.InputDevice")
    def test_record_from_device_timeout(self, mock_input_device):
        """Test recording stops on timeout."""
        mock_device = MagicMock()
        mock_device.read_one.side_effect = BlockingIOError()
        mock_input_device.return_value = mock_device

        recorder = DeviceMacroRecorder("/dev/input/event0")
        start = time.time()
        recorder.record_from_device(timeout=0.1)
        elapsed = time.time() - start

        assert elapsed >= 0.1
        assert elapsed < 0.5  # Shouldn't take too long
        mock_device.grab.assert_called_once()
        mock_device.ungrab.assert_called_once()

    @patch("services.macro_engine.recorder.InputDevice")
    def test_record_from_device_grabs_and_ungrabs(self, mock_input_device):
        """Test device is grabbed and ungrabbed."""
        mock_device = MagicMock()
        mock_device.read_one.side_effect = BlockingIOError()
        mock_input_device.return_value = mock_device

        recorder = DeviceMacroRecorder("/dev/input/event0")
        recorder.record_from_device(timeout=0.05)

        mock_device.grab.assert_called_once()
        mock_device.ungrab.assert_called_once()

    @patch("services.macro_engine.recorder.InputDevice")
    def test_record_from_device_with_callback(self, mock_input_device):
        """Test callback is set when provided."""
        mock_device = MagicMock()
        mock_device.read_one.side_effect = BlockingIOError()
        mock_input_device.return_value = mock_device

        callback = MagicMock()
        recorder = DeviceMacroRecorder("/dev/input/event0")
        recorder.record_from_device(timeout=0.05, on_event=callback)

        assert recorder._on_event == callback


class TestRecordEventEdgeCases:
    """Tests for edge cases in record_event method."""

    def test_unknown_key_code_returns_false(self, recorder):
        """Test record_event returns False when key code has no name (line 95)."""
        recorder.start()
        # Use a code that doesn't exist in KEY or BTN
        event = InputEvent(0, 0, ecodes.EV_KEY, 9999, 1)  # Invalid code
        result = recorder.record_event(event)
        assert result is False

    def test_list_code_name_uses_first(self, recorder):
        """Test code_name list uses first element (line 98)."""
        recorder.start()

        # Mock BTN.get to return a list (evdev actually returns tuples)
        with patch.dict(ecodes.BTN, {ecodes.BTN_LEFT: ["BTN_LEFT", "BTN_MOUSE"]}):
            event = make_key_event(ecodes.BTN_LEFT, 1)
            result = recorder.record_event(event)
            assert result is True
            assert recorder.get_event_count() == 1


class TestDeviceRecordingLoop:
    """Tests for the device reading loop in record_from_device."""

    @patch("services.macro_engine.recorder.InputDevice")
    def test_reads_events_and_records(self, mock_input_device):
        """Test reading events from device and recording them (lines 264-278)."""
        mock_device = MagicMock()

        # Create key events that will be read
        key_a_down = InputEvent(1, 0, ecodes.EV_KEY, ecodes.KEY_A, 1)
        key_a_up = InputEvent(1, 50000, ecodes.EV_KEY, ecodes.KEY_A, 0)

        # read_one() succeeds first, then BlockingIOError for rest
        read_one_count = [0]
        def read_one_side_effect():
            read_one_count[0] += 1
            if read_one_count[0] == 1:
                return key_a_down  # Has data
            raise BlockingIOError()

        # read() returns our events
        mock_device.read_one.side_effect = read_one_side_effect
        mock_device.read.return_value = [key_a_down, key_a_up]
        mock_input_device.return_value = mock_device

        recorder = DeviceMacroRecorder("/dev/input/event0")
        macro = recorder.record_from_device(timeout=0.05)

        # Should have recorded the key events
        assert recorder.get_event_count() >= 1

    @patch("services.macro_engine.recorder.InputDevice")
    def test_stop_key_stops_recording(self, mock_input_device):
        """Test pressing stop key stops recording (line 276)."""
        mock_device = MagicMock()

        # Create F12 key down event (default stop key)
        f12_down = InputEvent(1, 0, ecodes.EV_KEY, ecodes.KEY_F12, 1)

        # read_one() succeeds to indicate data available
        mock_device.read_one.return_value = f12_down
        mock_device.read.return_value = [f12_down]
        mock_input_device.return_value = mock_device

        recorder = DeviceMacroRecorder("/dev/input/event0", stop_key="F12")
        macro = recorder.record_from_device(timeout=5.0)  # Long timeout

        # Should have stopped early due to F12
        mock_device.ungrab.assert_called_once()

    @patch("services.macro_engine.recorder.InputDevice")
    def test_skips_non_key_events_in_loop(self, mock_input_device):
        """Test non-EV_KEY events are skipped in reading loop (line 265-266)."""
        mock_device = MagicMock()

        # Create a relative movement event (not EV_KEY)
        rel_event = InputEvent(1, 0, ecodes.EV_REL, ecodes.REL_X, 10)
        key_event = InputEvent(1, 50000, ecodes.EV_KEY, ecodes.KEY_A, 1)

        # read_one succeeds first then blocks
        read_one_count = [0]
        def read_one_side_effect():
            read_one_count[0] += 1
            if read_one_count[0] == 1:
                return rel_event
            raise BlockingIOError()

        mock_device.read_one.side_effect = read_one_side_effect
        mock_device.read.return_value = [rel_event, key_event]
        mock_input_device.return_value = mock_device

        recorder = DeviceMacroRecorder("/dev/input/event0")
        recorder.record_from_device(timeout=0.05)

        # Only key event should be recorded (rel_event skipped)
        assert recorder.get_event_count() == 1

    @patch("services.macro_engine.recorder.InputDevice")
    def test_stop_key_with_list_code_name(self, mock_input_device):
        """Test stop key detection when code returns list (line 272-273)."""
        mock_device = MagicMock()

        # Use KEY_F12 which we can mock to return a list
        f12_down = InputEvent(1, 0, ecodes.EV_KEY, ecodes.KEY_F12, 1)

        mock_device.read_one.return_value = f12_down
        mock_device.read.return_value = [f12_down]
        mock_input_device.return_value = mock_device

        # Mock KEY.get to return a list (evdev normally returns tuples)
        with patch.dict(ecodes.KEY, {ecodes.KEY_F12: ["KEY_F12", "KEY_F12_ALT"]}):
            recorder = DeviceMacroRecorder("/dev/input/event0", stop_key="F12")
            recorder.record_from_device(timeout=5.0)

        # Should have stopped on F12
        mock_device.ungrab.assert_called_once()


class TestUngrabExceptionHandling:
    """Tests for exception handling in ungrab."""

    @patch("services.macro_engine.recorder.InputDevice")
    def test_ungrab_exception_handled(self, mock_input_device):
        """Test ungrab exception is caught and ignored (lines 284-285)."""
        mock_device = MagicMock()
        mock_device.read_one.side_effect = BlockingIOError()
        mock_device.ungrab.side_effect = OSError("Device disconnected")
        mock_input_device.return_value = mock_device

        recorder = DeviceMacroRecorder("/dev/input/event0")
        # Should not raise exception
        macro = recorder.record_from_device(timeout=0.05)

        mock_device.ungrab.assert_called_once()
        # Should still return a valid macro
        assert macro is not None


class TestComplexMacroSequences:
    """Tests for complex macro recording scenarios."""

    def test_multiple_rapid_presses(self, recorder):
        """Test recording multiple rapid key presses."""
        recorder.start()
        recorder._events = [
            RecordedEvent(timestamp=1.0, code=ecodes.KEY_A, value=1, key_name="A"),
            RecordedEvent(timestamp=1.02, code=ecodes.KEY_A, value=0, key_name="A"),
            RecordedEvent(timestamp=1.05, code=ecodes.KEY_B, value=1, key_name="B"),
            RecordedEvent(timestamp=1.07, code=ecodes.KEY_B, value=0, key_name="B"),
            RecordedEvent(timestamp=1.1, code=ecodes.KEY_C, value=1, key_name="C"),
            RecordedEvent(timestamp=1.12, code=ecodes.KEY_C, value=0, key_name="C"),
        ]
        macro = recorder.stop()

        press_steps = [s for s in macro.steps if s.type == MacroStepType.KEY_PRESS]
        assert len(press_steps) == 3
        assert press_steps[0].key == "A"
        assert press_steps[1].key == "B"
        assert press_steps[2].key == "C"

    def test_interleaved_keys(self, recorder_no_merge):
        """Test recording interleaved key presses (A down, B down, A up, B up)."""
        recorder_no_merge.start()
        recorder_no_merge._events = [
            RecordedEvent(timestamp=1.0, code=ecodes.KEY_A, value=1, key_name="A"),
            RecordedEvent(timestamp=1.1, code=ecodes.KEY_B, value=1, key_name="B"),
            RecordedEvent(timestamp=1.2, code=ecodes.KEY_A, value=0, key_name="A"),
            RecordedEvent(timestamp=1.3, code=ecodes.KEY_B, value=0, key_name="B"),
        ]
        macro = recorder_no_merge.stop()

        # Check order: A down, B down, A up, B up (with delays)
        key_types = (MacroStepType.KEY_DOWN, MacroStepType.KEY_UP)
        key_steps = [s for s in macro.steps if s.type in key_types]
        assert len(key_steps) == 4
        assert key_steps[0].type == MacroStepType.KEY_DOWN
        assert key_steps[0].key == "A"
        assert key_steps[1].type == MacroStepType.KEY_DOWN
        assert key_steps[1].key == "B"
        assert key_steps[2].type == MacroStepType.KEY_UP
        assert key_steps[2].key == "A"
        assert key_steps[3].type == MacroStepType.KEY_UP
        assert key_steps[3].key == "B"
