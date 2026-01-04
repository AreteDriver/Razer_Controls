"""Tests for RemapEngine - core remapping logic."""

from unittest.mock import MagicMock, call

import pytest
from evdev import InputEvent, ecodes

from crates.profile_schema import (
    ActionType,
    Binding,
    Layer,
    MacroAction,
    MacroStep,
    MacroStepType,
    Profile,
)
from services.remap_daemon.engine import KeyState, RemapEngine

# --- Fixtures ---


@pytest.fixture
def mock_uinput():
    """Create a mock UInput device."""
    uinput = MagicMock()
    uinput.write = MagicMock()
    uinput.syn = MagicMock()
    return uinput


@pytest.fixture
def empty_profile():
    """Create an empty profile."""
    return Profile(
        id="test",
        name="Test Profile",
        layers=[Layer(id="base", name="Base Layer", bindings=[])],
    )


@pytest.fixture
def simple_profile():
    """Create a profile with basic bindings."""
    return Profile(
        id="test",
        name="Test Profile",
        layers=[
            Layer(
                id="base",
                name="Base Layer",
                bindings=[
                    # BTN_SIDE (mouse side button) -> KEY_A
                    Binding(
                        input_code="BTN_SIDE",
                        action_type=ActionType.KEY,
                        output_keys=["A"],
                    ),
                    # BTN_EXTRA -> Chord (Ctrl+C)
                    Binding(
                        input_code="BTN_EXTRA",
                        action_type=ActionType.CHORD,
                        output_keys=["CTRL", "C"],
                    ),
                    # BTN_FORWARD -> Disabled
                    Binding(
                        input_code="BTN_FORWARD",
                        action_type=ActionType.DISABLED,
                        output_keys=[],
                    ),
                    # BTN_BACK -> Passthrough
                    Binding(
                        input_code="BTN_BACK",
                        action_type=ActionType.PASSTHROUGH,
                        output_keys=[],
                    ),
                ],
            )
        ],
    )


@pytest.fixture
def macro_profile():
    """Create a profile with macro bindings."""
    return Profile(
        id="test",
        name="Test Macro Profile",
        macros=[
            MacroAction(
                id="test_macro",
                name="Test Macro",
                steps=[
                    MacroStep(type=MacroStepType.KEY_PRESS, key="A"),
                    MacroStep(type=MacroStepType.DELAY, delay_ms=10),
                    MacroStep(type=MacroStepType.KEY_PRESS, key="B"),
                ],
                repeat_count=1,
            ),
        ],
        layers=[
            Layer(
                id="base",
                name="Base Layer",
                bindings=[
                    Binding(
                        input_code="BTN_SIDE",
                        action_type=ActionType.MACRO,
                        macro_id="test_macro",
                    ),
                ],
            )
        ],
    )


@pytest.fixture
def hypershift_profile():
    """Create a profile with Hypershift-style layer."""
    return Profile(
        id="test",
        name="Hypershift Profile",
        layers=[
            Layer(
                id="base",
                name="Base Layer",
                bindings=[
                    Binding(
                        input_code="BTN_SIDE",
                        action_type=ActionType.KEY,
                        output_keys=["A"],
                    ),
                ],
            ),
            Layer(
                id="shift",
                name="Shift Layer",
                hold_modifier_input_code="BTN_EXTRA",  # Hold to activate
                bindings=[
                    Binding(
                        input_code="BTN_SIDE",
                        action_type=ActionType.KEY,
                        output_keys=["B"],  # Different output on shift layer
                    ),
                ],
            ),
        ],
    )


def make_key_event(code: int, value: int) -> InputEvent:
    """Create a key event."""
    return InputEvent(0, 0, ecodes.EV_KEY, code, value)


# --- Test Classes ---


class TestKeyState:
    """Tests for KeyState dataclass."""

    def test_default_state(self):
        """Test default key state."""
        state = KeyState()
        assert state.active_layer == "base"
        assert len(state.physical_pressed) == 0
        assert len(state.active_bindings) == 0
        assert len(state.output_held) == 0
        assert state.layer_modifier_held is None


class TestRemapEngineInit:
    """Tests for RemapEngine initialization."""

    def test_init_empty_profile(self, empty_profile):
        """Test initialization with empty profile."""
        engine = RemapEngine(empty_profile)
        assert engine.profile == empty_profile
        assert "base" in engine._bindings
        assert len(engine._bindings["base"]) == 0

    def test_init_with_bindings(self, simple_profile):
        """Test initialization builds lookup tables."""
        engine = RemapEngine(simple_profile)
        assert "base" in engine._bindings
        # BTN_SIDE code is 0x116 (278)
        assert ecodes.BTN_SIDE in engine._bindings["base"]

    def test_init_with_macros(self, macro_profile):
        """Test initialization indexes macros."""
        engine = RemapEngine(macro_profile)
        assert "test_macro" in engine._macros
        assert engine._macros["test_macro"].name == "Test Macro"

    def test_init_with_layers(self, hypershift_profile):
        """Test initialization with multiple layers."""
        engine = RemapEngine(hypershift_profile)
        assert "base" in engine._bindings
        assert "shift" in engine._bindings
        # BTN_EXTRA is the layer modifier
        assert ecodes.BTN_EXTRA in engine._layer_modifiers


class TestKeyBinding:
    """Tests for basic key binding."""

    def test_key_binding_down(self, simple_profile, mock_uinput):
        """Test key binding on key down."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Press BTN_SIDE
        event = make_key_event(ecodes.BTN_SIDE, 1)
        handled = engine.process_event(event)

        assert handled is True
        # Should emit KEY_A down
        mock_uinput.write.assert_called_with(ecodes.EV_KEY, ecodes.KEY_A, 1)

    def test_key_binding_up(self, simple_profile, mock_uinput):
        """Test key binding on key up."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Press and release BTN_SIDE
        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))
        mock_uinput.reset_mock()

        event = make_key_event(ecodes.BTN_SIDE, 0)
        handled = engine.process_event(event)

        assert handled is True
        # Should emit KEY_A up
        mock_uinput.write.assert_called_with(ecodes.EV_KEY, ecodes.KEY_A, 0)

    def test_unbound_key_passthrough(self, simple_profile, mock_uinput):
        """Test unbound key passes through."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Press an unbound key
        event = make_key_event(ecodes.KEY_Q, 1)
        handled = engine.process_event(event)

        assert handled is False
        mock_uinput.write.assert_not_called()


class TestChordBinding:
    """Tests for chord bindings."""

    def test_chord_down(self, simple_profile, mock_uinput):
        """Test chord binding emits all keys."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Press BTN_EXTRA (bound to Ctrl+C)
        event = make_key_event(ecodes.BTN_EXTRA, 1)
        handled = engine.process_event(event)

        assert handled is True
        # Should emit CTRL and C in order
        calls = mock_uinput.write.call_args_list
        assert len(calls) == 2
        assert calls[0] == call(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 1)
        assert calls[1] == call(ecodes.EV_KEY, ecodes.KEY_C, 1)

    def test_chord_up_releases_in_reverse(self, simple_profile, mock_uinput):
        """Test chord releases keys in reverse order."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Press and release BTN_EXTRA
        engine.process_event(make_key_event(ecodes.BTN_EXTRA, 1))
        mock_uinput.reset_mock()

        engine.process_event(make_key_event(ecodes.BTN_EXTRA, 0))

        # Should release C then CTRL (reverse order)
        calls = mock_uinput.write.call_args_list
        assert len(calls) == 2
        assert calls[0] == call(ecodes.EV_KEY, ecodes.KEY_C, 0)
        assert calls[1] == call(ecodes.EV_KEY, ecodes.KEY_LEFTCTRL, 0)


class TestDisabledBinding:
    """Tests for disabled bindings."""

    def test_disabled_consumes_event(self, simple_profile, mock_uinput):
        """Test disabled binding consumes event without output."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Press BTN_FORWARD (disabled)
        event = make_key_event(ecodes.BTN_FORWARD, 1)
        handled = engine.process_event(event)

        assert handled is True
        # No output should be emitted
        mock_uinput.write.assert_not_called()


class TestPassthroughBinding:
    """Tests for passthrough bindings."""

    def test_passthrough_emits_original(self, simple_profile, mock_uinput):
        """Test passthrough emits original key."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Press BTN_BACK (passthrough)
        event = make_key_event(ecodes.BTN_BACK, 1)
        handled = engine.process_event(event)

        assert handled is True
        mock_uinput.write.assert_called_with(ecodes.EV_KEY, ecodes.BTN_BACK, 1)


class TestMacroBinding:
    """Tests for macro bindings."""

    def test_macro_executes_steps(self, macro_profile, mock_uinput):
        """Test macro executes all steps."""
        engine = RemapEngine(macro_profile)
        engine.set_uinput(mock_uinput)

        # Press BTN_SIDE (macro)
        event = make_key_event(ecodes.BTN_SIDE, 1)
        handled = engine.process_event(event)

        assert handled is True
        # Should have key presses for A and B
        calls = [c for c in mock_uinput.write.call_args_list]
        # KEY_PRESS = down + up for each key
        assert len(calls) >= 4  # A down, A up, B down, B up


class TestLayerSwitching:
    """Tests for Hypershift-style layer switching."""

    def test_layer_modifier_activates_layer(self, hypershift_profile, mock_uinput):
        """Test holding layer modifier activates layer."""
        engine = RemapEngine(hypershift_profile)
        engine.set_uinput(mock_uinput)

        # Press BTN_EXTRA (layer modifier)
        engine.process_event(make_key_event(ecodes.BTN_EXTRA, 1))

        assert engine.state.active_layer == "shift"

    def test_layer_modifier_returns_to_base(self, hypershift_profile, mock_uinput):
        """Test releasing layer modifier returns to base."""
        engine = RemapEngine(hypershift_profile)
        engine.set_uinput(mock_uinput)

        # Press and release BTN_EXTRA
        engine.process_event(make_key_event(ecodes.BTN_EXTRA, 1))
        engine.process_event(make_key_event(ecodes.BTN_EXTRA, 0))

        assert engine.state.active_layer == "base"

    def test_key_uses_active_layer(self, hypershift_profile, mock_uinput):
        """Test keys use active layer binding."""
        engine = RemapEngine(hypershift_profile)
        engine.set_uinput(mock_uinput)

        # Press BTN_SIDE on base layer -> A
        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))
        assert mock_uinput.write.call_args == call(ecodes.EV_KEY, ecodes.KEY_A, 1)

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 0))
        mock_uinput.reset_mock()

        # Activate shift layer
        engine.process_event(make_key_event(ecodes.BTN_EXTRA, 1))

        # Press BTN_SIDE on shift layer -> B
        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))
        assert mock_uinput.write.call_args == call(ecodes.EV_KEY, ecodes.KEY_B, 1)


class TestStateManagement:
    """Tests for key state management."""

    def test_tracks_physical_pressed(self, simple_profile, mock_uinput):
        """Test tracks physically pressed keys."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))
        assert ecodes.BTN_SIDE in engine.state.physical_pressed

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 0))
        assert ecodes.BTN_SIDE not in engine.state.physical_pressed

    def test_tracks_active_bindings(self, simple_profile, mock_uinput):
        """Test tracks active bindings."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))
        assert ecodes.BTN_SIDE in engine.state.active_bindings

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 0))
        assert ecodes.BTN_SIDE not in engine.state.active_bindings

    def test_tracks_output_held(self, simple_profile, mock_uinput):
        """Test tracks held output keys."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))
        assert ecodes.KEY_A in engine.state.output_held

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 0))
        assert ecodes.KEY_A not in engine.state.output_held


class TestReleaseAllKeys:
    """Tests for release_all_keys cleanup."""

    def test_releases_all_held_keys(self, simple_profile, mock_uinput):
        """Test releases all held keys on shutdown."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Hold down some keys
        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))
        engine.process_event(make_key_event(ecodes.BTN_EXTRA, 1))
        mock_uinput.reset_mock()

        engine.release_all_keys()

        # Should have released all keys
        assert len(engine.state.active_bindings) == 0
        assert len(engine.state.output_held) == 0


class TestReloadProfile:
    """Tests for profile reloading."""

    def test_reload_clears_state(self, simple_profile, empty_profile, mock_uinput):
        """Test reload clears existing state."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Hold a key
        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))

        # Reload with empty profile
        engine.reload_profile(empty_profile)

        assert engine.profile == empty_profile
        assert len(engine.state.active_bindings) == 0
        assert engine.state.active_layer == "base"


class TestNonKeyEvents:
    """Tests for non-key events."""

    def test_non_key_events_passthrough(self, simple_profile, mock_uinput):
        """Test non-key events are not handled."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Create a relative mouse motion event
        event = InputEvent(0, 0, ecodes.EV_REL, ecodes.REL_X, 10)
        handled = engine.process_event(event)

        assert handled is False
        mock_uinput.write.assert_not_called()


class TestKeyRepeat:
    """Tests for key repeat events."""

    def test_repeat_consumed_for_bound_keys(self, simple_profile, mock_uinput):
        """Test repeat events are consumed for bound keys."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Press and then repeat
        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))
        mock_uinput.reset_mock()

        event = make_key_event(ecodes.BTN_SIDE, 2)  # 2 = repeat
        handled = engine.process_event(event)

        assert handled is True
        # No output on repeat
        mock_uinput.write.assert_not_called()


class TestGetLayerInfo:
    """Tests for get_layer_info debug method."""

    def test_returns_layer_state(self, hypershift_profile, mock_uinput):
        """Test returns current layer state."""
        engine = RemapEngine(hypershift_profile)
        engine.set_uinput(mock_uinput)

        info = engine.get_layer_info()

        assert info["active_layer"] == "base"
        assert "base" in info["available_layers"]
        assert "shift" in info["available_layers"]


class TestEdgeCases:
    """Tests for edge cases and uncovered code paths."""

    def test_invalid_event_value_returns_false(self, simple_profile, mock_uinput):
        """Test event with invalid value (not 0, 1, or 2) returns False (line 115)."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Value 3 is invalid
        event = InputEvent(0, 0, ecodes.EV_KEY, ecodes.BTN_SIDE, 3)
        handled = engine.process_event(event)

        assert handled is False

    def test_key_up_without_active_binding_returns_false(self, simple_profile, mock_uinput):
        """Test key up without prior press returns False (line 225)."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Release without pressing first
        event = make_key_event(ecodes.BTN_SIDE, 0)
        handled = engine.process_event(event)

        assert handled is False

    def test_key_repeat_for_unbound_key_returns_false(self, simple_profile, mock_uinput):
        """Test key repeat for unbound key returns False (line 232)."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Repeat for a key that was never pressed (not in active_bindings)
        event = make_key_event(ecodes.KEY_Q, 2)
        handled = engine.process_event(event)

        assert handled is False


class TestLayerConflicts:
    """Tests for layer switching with conflicting keys."""

    def test_release_conflicting_keys_on_layer_change(self, mock_uinput):
        """Test keys are released when layer binding differs (lines 150-158)."""
        # Profile where BTN_SIDE maps to A on base, B on shift
        profile = Profile(
            id="test",
            name="Conflict Profile",
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(input_code="BTN_SIDE", action_type=ActionType.KEY, output_keys=["A"]),
                    ],
                ),
                Layer(
                    id="shift",
                    name="Shift",
                    hold_modifier_input_code="BTN_EXTRA",
                    bindings=[
                        Binding(input_code="BTN_SIDE", action_type=ActionType.KEY, output_keys=["B"]),
                    ],
                ),
            ],
        )
        engine = RemapEngine(profile)
        engine.set_uinput(mock_uinput)

        # Press BTN_SIDE on base layer (outputs A)
        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))
        assert ecodes.KEY_A in engine.state.output_held
        mock_uinput.reset_mock()

        # Activate shift layer while holding BTN_SIDE
        engine.process_event(make_key_event(ecodes.BTN_EXTRA, 1))

        # A should be released because BTN_SIDE has different binding on shift
        release_calls = [c for c in mock_uinput.write.call_args_list if c[0][2] == 0]
        assert any(c[0][1] == ecodes.KEY_A for c in release_calls)

    def test_release_layer_keys_on_modifier_release(self, mock_uinput):
        """Test layer-specific keys are released on modifier release (lines 165-169)."""
        profile = Profile(
            id="test",
            name="Layer Release Profile",
            layers=[
                Layer(id="base", name="Base", bindings=[]),
                Layer(
                    id="shift",
                    name="Shift",
                    hold_modifier_input_code="BTN_EXTRA",
                    bindings=[
                        Binding(input_code="BTN_SIDE", action_type=ActionType.KEY, output_keys=["B"]),
                    ],
                ),
            ],
        )
        engine = RemapEngine(profile)
        engine.set_uinput(mock_uinput)

        # Activate shift layer
        engine.process_event(make_key_event(ecodes.BTN_EXTRA, 1))

        # Press BTN_SIDE on shift layer
        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))
        assert ecodes.KEY_B in engine.state.output_held
        mock_uinput.reset_mock()

        # Release layer modifier - should release shift layer keys
        engine.process_event(make_key_event(ecodes.BTN_EXTRA, 0))

        # B should be released
        release_calls = [c for c in mock_uinput.write.call_args_list if c[0][2] == 0]
        assert any(c[0][1] == ecodes.KEY_B for c in release_calls)


class TestMacroStepTypes:
    """Tests for all macro step types."""

    def test_macro_key_down_step(self, mock_uinput):
        """Test KEY_DOWN macro step (lines 306-309)."""
        profile = Profile(
            id="test",
            name="Key Down Macro",
            macros=[
                MacroAction(
                    id="keydown_macro",
                    name="Key Down Macro",
                    steps=[MacroStep(type=MacroStepType.KEY_DOWN, key="A")],
                    repeat_count=1,
                ),
            ],
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(input_code="BTN_SIDE", action_type=ActionType.MACRO, macro_id="keydown_macro"),
                    ],
                )
            ],
        )
        engine = RemapEngine(profile)
        engine.set_uinput(mock_uinput)

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))

        # Should have KEY_A down
        calls = mock_uinput.write.call_args_list
        assert any(c[0] == (ecodes.EV_KEY, ecodes.KEY_A, 1) for c in calls)

    def test_macro_key_up_step(self, mock_uinput):
        """Test KEY_UP macro step (lines 312-315)."""
        profile = Profile(
            id="test",
            name="Key Up Macro",
            macros=[
                MacroAction(
                    id="keyup_macro",
                    name="Key Up Macro",
                    steps=[MacroStep(type=MacroStepType.KEY_UP, key="A")],
                    repeat_count=1,
                ),
            ],
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(input_code="BTN_SIDE", action_type=ActionType.MACRO, macro_id="keyup_macro"),
                    ],
                )
            ],
        )
        engine = RemapEngine(profile)
        engine.set_uinput(mock_uinput)

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))

        # Should have KEY_A up
        calls = mock_uinput.write.call_args_list
        assert any(c[0] == (ecodes.EV_KEY, ecodes.KEY_A, 0) for c in calls)

    def test_macro_text_step(self, mock_uinput):
        """Test TEXT macro step (lines 329-331)."""
        profile = Profile(
            id="test",
            name="Text Macro",
            macros=[
                MacroAction(
                    id="text_macro",
                    name="Text Macro",
                    steps=[MacroStep(type=MacroStepType.TEXT, text="ab")],
                    repeat_count=1,
                ),
            ],
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(input_code="BTN_SIDE", action_type=ActionType.MACRO, macro_id="text_macro"),
                    ],
                )
            ],
        )
        engine = RemapEngine(profile)
        engine.set_uinput(mock_uinput)

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))

        # Should have typed 'a' and 'b'
        calls = mock_uinput.write.call_args_list
        a_pressed = any(c[0] == (ecodes.EV_KEY, ecodes.KEY_A, 1) for c in calls)
        b_pressed = any(c[0] == (ecodes.EV_KEY, ecodes.KEY_B, 1) for c in calls)
        assert a_pressed
        assert b_pressed

    def test_macro_text_with_uppercase(self, mock_uinput):
        """Test TEXT macro with uppercase letters (lines 356-366)."""
        profile = Profile(
            id="test",
            name="Uppercase Macro",
            macros=[
                MacroAction(
                    id="upper_macro",
                    name="Upper Macro",
                    steps=[MacroStep(type=MacroStepType.TEXT, text="AB")],
                    repeat_count=1,
                ),
            ],
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(input_code="BTN_SIDE", action_type=ActionType.MACRO, macro_id="upper_macro"),
                    ],
                )
            ],
        )
        engine = RemapEngine(profile)
        engine.set_uinput(mock_uinput)

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))

        # Should have shift pressed for uppercase
        calls = mock_uinput.write.call_args_list
        shift_pressed = any(c[0][1] == ecodes.KEY_LEFTSHIFT and c[0][2] == 1 for c in calls)
        assert shift_pressed

    def test_macro_text_with_special_chars(self, mock_uinput):
        """Test TEXT macro with space, enter, tab (lines 348-350)."""
        profile = Profile(
            id="test",
            name="Special Macro",
            macros=[
                MacroAction(
                    id="special_macro",
                    name="Special Macro",
                    steps=[MacroStep(type=MacroStepType.TEXT, text="a b")],  # Has space
                    repeat_count=1,
                ),
            ],
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(input_code="BTN_SIDE", action_type=ActionType.MACRO, macro_id="special_macro"),
                    ],
                )
            ],
        )
        engine = RemapEngine(profile)
        engine.set_uinput(mock_uinput)

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))

        # Should have space key
        calls = mock_uinput.write.call_args_list
        space_pressed = any(c[0][1] == ecodes.KEY_SPACE for c in calls)
        assert space_pressed

    def test_macro_text_with_numbers(self, mock_uinput):
        """Test TEXT macro with numbers (lines 345-347)."""
        profile = Profile(
            id="test",
            name="Number Macro",
            macros=[
                MacroAction(
                    id="num_macro",
                    name="Number Macro",
                    steps=[MacroStep(type=MacroStepType.TEXT, text="12")],
                    repeat_count=1,
                ),
            ],
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(input_code="BTN_SIDE", action_type=ActionType.MACRO, macro_id="num_macro"),
                    ],
                )
            ],
        )
        engine = RemapEngine(profile)
        engine.set_uinput(mock_uinput)

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))

        # Should have 1 and 2 keys
        calls = mock_uinput.write.call_args_list
        one_pressed = any(c[0][1] == ecodes.KEY_1 for c in calls)
        two_pressed = any(c[0][1] == ecodes.KEY_2 for c in calls)
        assert one_pressed
        assert two_pressed

    def test_macro_text_skips_unknown_chars(self, mock_uinput):
        """Test TEXT macro skips unknown characters (line 352)."""
        profile = Profile(
            id="test",
            name="Unknown Char Macro",
            macros=[
                MacroAction(
                    id="unknown_macro",
                    name="Unknown Macro",
                    steps=[MacroStep(type=MacroStepType.TEXT, text="a@b")],  # @ is skipped
                    repeat_count=1,
                ),
            ],
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(input_code="BTN_SIDE", action_type=ActionType.MACRO, macro_id="unknown_macro"),
                    ],
                )
            ],
        )
        engine = RemapEngine(profile)
        engine.set_uinput(mock_uinput)

        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))

        # Should have a and b but not @
        calls = mock_uinput.write.call_args_list
        a_pressed = any(c[0] == (ecodes.EV_KEY, ecodes.KEY_A, 1) for c in calls)
        b_pressed = any(c[0] == (ecodes.EV_KEY, ecodes.KEY_B, 1) for c in calls)
        assert a_pressed
        assert b_pressed

    def test_macro_with_repeat_and_delay(self, mock_uinput):
        """Test macro with repeat and delay (line 301)."""
        profile = Profile(
            id="test",
            name="Repeat Macro",
            macros=[
                MacroAction(
                    id="repeat_macro",
                    name="Repeat Macro",
                    steps=[MacroStep(type=MacroStepType.KEY_PRESS, key="A")],
                    repeat_count=2,
                    repeat_delay_ms=10,
                ),
            ],
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(input_code="BTN_SIDE", action_type=ActionType.MACRO, macro_id="repeat_macro"),
                    ],
                )
            ],
        )
        engine = RemapEngine(profile)
        engine.set_uinput(mock_uinput)

        import time
        start = time.time()
        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))
        elapsed = time.time() - start

        # Should have taken at least 10ms for the delay
        assert elapsed >= 0.01

        # Should have pressed A twice (2 repeats)
        calls = mock_uinput.write.call_args_list
        a_presses = [c for c in calls if c[0] == (ecodes.EV_KEY, ecodes.KEY_A, 1)]
        assert len(a_presses) == 2


class TestReleaseActiveBindingEdgeCases:
    """Tests for _release_active_binding edge cases."""

    def test_release_inactive_binding_does_nothing(self, simple_profile, mock_uinput):
        """Test releasing a binding that isn't active does nothing (line 174)."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Try to release a binding that was never pressed
        engine._release_active_binding(ecodes.BTN_SIDE)

        # Should not crash or emit anything
        mock_uinput.write.assert_not_called()


class TestReleaseAllKeysOutputHeld:
    """Tests for release_all_keys safety code."""

    def test_release_all_clears_orphan_output_held(self, simple_profile, mock_uinput):
        """Test release_all_keys clears orphaned output_held entries (line 378)."""
        engine = RemapEngine(simple_profile)
        engine.set_uinput(mock_uinput)

        # Manually add an orphaned output key (simulates a bug where active_bindings was cleared but output_held wasn't)
        engine.state.output_held.add(ecodes.KEY_X)
        mock_uinput.reset_mock()

        engine.release_all_keys()

        # Should release the orphaned key
        mock_uinput.write.assert_called_with(ecodes.EV_KEY, ecodes.KEY_X, 0)
        assert len(engine.state.output_held) == 0


class TestLayerFallback:
    """Tests for layer binding fallback behavior."""

    def test_fallback_to_base_layer(self, mock_uinput):
        """Test binding falls back to base layer (line 248)."""
        profile = Profile(
            id="test",
            name="Fallback Profile",
            layers=[
                Layer(
                    id="base",
                    name="Base",
                    bindings=[
                        Binding(input_code="BTN_SIDE", action_type=ActionType.KEY, output_keys=["A"]),
                    ],
                ),
                Layer(
                    id="shift",
                    name="Shift",
                    hold_modifier_input_code="BTN_EXTRA",
                    bindings=[],  # No bindings in shift layer
                ),
            ],
        )
        engine = RemapEngine(profile)
        engine.set_uinput(mock_uinput)

        # Activate shift layer
        engine.process_event(make_key_event(ecodes.BTN_EXTRA, 1))
        assert engine.state.active_layer == "shift"

        # Press BTN_SIDE - should fall back to base layer binding
        engine.process_event(make_key_event(ecodes.BTN_SIDE, 1))

        # Should emit A (from base layer)
        calls = mock_uinput.write.call_args_list
        assert any(c[0] == (ecodes.EV_KEY, ecodes.KEY_A, 1) for c in calls)
