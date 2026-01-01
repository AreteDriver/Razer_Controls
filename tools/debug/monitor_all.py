#!/usr/bin/env python3
"""Monitor ALL Basilisk devices for button presses."""
import select
import sys

from evdev import InputDevice, ecodes

sys.stdout.reconfigure(line_buffering=True)

# Find all devices
devices = []
for path in ['/dev/input/event8', '/dev/input/event11', '/dev/input/event19']:
    try:
        dev = InputDevice(path)
        devices.append(dev)
        print(f"Monitoring: {path} - {dev.name}")
    except Exception as e:
        print(f"Cannot open {path}: {e}")

print("\nPress ALL mouse buttons including the two THUMB buttons on the LEFT SIDE!")
print("Press Ctrl+C to stop\n")

try:
    while True:
        r, _, _ = select.select([d.fd for d in devices], [], [], 0.1)
        for dev in devices:
            if dev.fd in r:
                for event in dev.read():
                    if event.type == ecodes.EV_KEY:
                        name = ecodes.BTN.get(
                            event.code, ecodes.KEY.get(event.code, str(event.code))
                        )
                        if isinstance(name, list):
                            name = name[0]
                        action = "DOWN" if event.value == 1 else "UP"
                        print(f"  [{dev.path}] {name}: {action}")
except KeyboardInterrupt:
    print("\nDone")
