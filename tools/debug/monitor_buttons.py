#!/usr/bin/env python3
"""Monitor mouse button presses - run this and click all buttons!"""

import select
import sys

from evdev import InputDevice, ecodes

# Unbuffered output
sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

dev = InputDevice("/dev/input/event8")
print(f"Monitoring: {dev.name}")
print("Click ALL mouse buttons including thumb buttons!")
print("Press Ctrl+C to stop\n")

try:
    while True:
        r, _, _ = select.select([dev.fd], [], [], 0.1)
        if r:
            for event in dev.read():
                if event.type == ecodes.EV_KEY:
                    name = ecodes.BTN.get(event.code, ecodes.KEY.get(event.code, str(event.code)))
                    if isinstance(name, list):
                        name = name[0]
                    action = "DOWN" if event.value == 1 else "UP" if event.value == 0 else "HOLD"
                    print(f"  {name}: {action}")
except KeyboardInterrupt:
    print("\nDone")
