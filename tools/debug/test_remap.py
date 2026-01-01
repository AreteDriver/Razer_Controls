#!/usr/bin/env python3
"""Test script for the remap daemon - runs for 15 seconds."""

import signal
import sys
import time
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from evdev import InputDevice, UInput, ecodes

from crates.device_registry import DeviceRegistry
from crates.profile_schema import ProfileLoader
from services.remap_daemon.engine import RemapEngine


def main():
    print("=" * 60)
    print("REMAP DAEMON TEST")
    print("=" * 60)
    print()
    print("This test will:")
    print("  1. Grab your Basilisk V2 mouse")
    print("  2. Remap BTN_SIDE (back thumb) -> F13")
    print("  3. Remap BTN_EXTRA (forward thumb) -> Ctrl+C")
    print("  4. Run for 15 seconds, then release")
    print()
    print("While running, try pressing the side buttons!")
    print("Open a text editor to see if Ctrl+C copies text.")
    print()
    print("-" * 60)

    # Load profile
    loader = ProfileLoader()
    profile = loader.load_active_profile()

    if not profile:
        print("ERROR: No active profile found")
        return 1

    print(f"Loaded profile: {profile.name}")
    print(f"Input devices: {profile.input_devices}")
    print(f"Bindings: {len(profile.layers[0].bindings) if profile.layers else 0}")

    for layer in profile.layers:
        for binding in layer.bindings:
            output = binding.output_keys or binding.macro_id
            print(f"  {binding.input_code} -> {binding.action_type.value}: {output}")

    print()

    # Find the device
    registry = DeviceRegistry()
    device_id = profile.input_devices[0] if profile.input_devices else None

    if not device_id:
        print("ERROR: No input device configured")
        return 1

    event_path = registry.get_event_path(device_id)
    if not event_path:
        print(f"ERROR: Could not find device {device_id}")
        return 1

    print(f"Device path: {event_path}")

    # Create engine
    engine = RemapEngine(profile)

    # Create uinput
    try:
        capabilities = {
            ecodes.EV_KEY: list(range(0, 256)) + list(range(0x110, 0x120)),
            ecodes.EV_REL: [ecodes.REL_X, ecodes.REL_Y, ecodes.REL_WHEEL, ecodes.REL_HWHEEL],
        }
        uinput = UInput(capabilities, name="Razer Remap Test")
        engine.set_uinput(uinput)
        print(f"Created virtual device: {uinput.name}")
    except Exception as e:
        print(f"ERROR: Failed to create uinput: {e}")
        return 1

    # Open and grab the device
    try:
        device = InputDevice(event_path)
        device.grab()
        print(f"Grabbed: {device.name}")
    except PermissionError:
        print(f"ERROR: Permission denied for {event_path}")
        print("You may need to be in the 'input' or 'plugdev' group")
        uinput.close()
        return 1
    except Exception as e:
        print(f"ERROR: Failed to grab device: {e}")
        uinput.close()
        return 1

    print()
    print("=" * 60)
    print("RUNNING - Press side buttons to test! (15 seconds)")
    print("=" * 60)
    print()

    start_time = time.time()
    timeout = 15  # seconds

    def signal_handler(sig, frame):
        nonlocal timeout
        timeout = 0

    signal.signal(signal.SIGINT, signal_handler)

    try:
        while time.time() - start_time < timeout:
            # Non-blocking read with select
            import select
            r, _, _ = select.select([device.fd], [], [], 0.1)

            if r:
                for event in device.read():
                    # Show raw event
                    if event.type == ecodes.EV_KEY:
                        key_name = (
                            ecodes.KEY.get(event.code)
                            or ecodes.BTN.get(event.code)
                            or event.code
                        )
                        if event.value == 1:
                            state = "DOWN"
                        elif event.value == 0:
                            state = "UP"
                        else:
                            state = "REPEAT"
                        print(f"  Input: {key_name} {state}")

                    # Process through engine
                    handled = engine.process_event(event)

                    if not handled:
                        # Pass through
                        uinput.write_event(event)
                        if event.type != ecodes.EV_SYN:
                            uinput.syn()

            # Show countdown
            remaining = int(timeout - (time.time() - start_time))
            if remaining >= 0 and remaining % 5 == 0:
                pass  # Could show countdown here

    except Exception as e:
        print(f"Error: {e}")

    finally:
        print()
        print("=" * 60)
        print("TEST COMPLETE - Releasing device")
        print("=" * 60)

        try:
            device.ungrab()
            print("Device released")
        except OSError:
            pass

        try:
            uinput.close()
            print("Virtual device closed")
        except OSError:
            pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
