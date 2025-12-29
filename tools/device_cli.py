"""CLI tool for controlling Razer hardware via OpenRazer.

Usage:
    razer-device list                          # List all Razer devices
    razer-device info <serial>                 # Show device details
    razer-device dpi <serial> <value>          # Set DPI (e.g., 800 or 800x600)
    razer-device brightness <serial> <0-100>   # Set brightness
    razer-device poll-rate <serial> <rate>     # Set poll rate (125/500/1000)
    razer-device effect <serial> <effect>      # Set lighting effect
    razer-device color <serial> <r> <g> <b>    # Set static color
"""

import argparse
import sys
from typing import Optional

from services.openrazer_bridge import (
    OpenRazerBridge,
    RazerDevice,
    WaveDirection,
    ReactiveSpeed,
)


def parse_color(color_str: str) -> Optional[tuple[int, int, int]]:
    """Parse color from various formats: 'FF0000', '#FF0000', '255,0,0', '255 0 0'."""
    color_str = color_str.strip().lstrip("#")

    # Hex format
    if len(color_str) == 6 and all(c in "0123456789abcdefABCDEF" for c in color_str):
        r = int(color_str[0:2], 16)
        g = int(color_str[2:4], 16)
        b = int(color_str[4:6], 16)
        return (r, g, b)

    # Comma or space separated
    for sep in [",", " "]:
        if sep in color_str:
            parts = [p.strip() for p in color_str.split(sep) if p.strip()]
            if len(parts) == 3:
                try:
                    r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                    if all(0 <= c <= 255 for c in (r, g, b)):
                        return (r, g, b)
                except ValueError:
                    pass

    return None


def get_bridge() -> Optional[OpenRazerBridge]:
    """Get connected OpenRazer bridge."""
    bridge = OpenRazerBridge()
    if not bridge.connect():
        print("Error: Could not connect to OpenRazer daemon.")
        print("Is openrazer-daemon running?")
        print("  sudo systemctl start openrazer-daemon")
        return None
    return bridge


def find_device(bridge: OpenRazerBridge, identifier: str) -> Optional[RazerDevice]:
    """Find a device by serial or partial name match."""
    devices = bridge.discover_devices()

    # Exact serial match
    for dev in devices:
        if dev.serial == identifier:
            return dev

    # Partial name match (case insensitive)
    identifier_lower = identifier.lower()
    for dev in devices:
        if identifier_lower in dev.name.lower():
            return dev
        if identifier_lower in dev.serial.lower():
            return dev

    # Index match (0, 1, 2...)
    try:
        idx = int(identifier)
        if 0 <= idx < len(devices):
            return devices[idx]
    except ValueError:
        pass

    return None


def cmd_list(args) -> int:
    """List all Razer devices."""
    bridge = get_bridge()
    if not bridge:
        return 1

    devices = bridge.discover_devices()

    if not devices:
        print("No Razer devices found.")
        print("\nMake sure:")
        print("  1. OpenRazer is installed (openrazer-daemon)")
        print("  2. Your device is supported by OpenRazer")
        return 0

    print(f"\n{'#':<3} {'Name':<35} {'Type':<12} {'Serial'}")
    print("-" * 70)

    for i, dev in enumerate(devices):
        print(f"{i:<3} {dev.name:<35} {dev.device_type:<12} {dev.serial}")

    print(f"\n{len(devices)} device(s) found.")
    print("\nUse 'razer-device info <serial>' for details.")
    return 0


def cmd_info(args) -> int:
    """Show detailed device information."""
    bridge = get_bridge()
    if not bridge:
        return 1

    device = find_device(bridge, args.device)
    if not device:
        print(f"Error: Device '{args.device}' not found.")
        print("Use 'razer-device list' to see available devices.")
        return 1

    print(f"\n{'=' * 60}")
    print(f"  {device.name}")
    print(f"{'=' * 60}")
    print(f"  Serial:    {device.serial}")
    print(f"  Type:      {device.device_type}")
    if device.firmware_version:
        print(f"  Firmware:  {device.firmware_version}")

    print(f"\n  Capabilities:")

    if device.has_dpi:
        print(f"    DPI:        Yes (current: {device.dpi[0]}x{device.dpi[1]}, max: {device.max_dpi})")
    else:
        print(f"    DPI:        No")

    if device.has_poll_rate:
        print(f"    Poll Rate:  Yes (current: {device.poll_rate} Hz)")
    else:
        print(f"    Poll Rate:  No")

    if device.has_brightness:
        print(f"    Brightness: Yes (current: {device.brightness}%)")
    else:
        print(f"    Brightness: No")

    if device.has_lighting:
        effects = ", ".join(device.supported_effects) if device.supported_effects else "unknown"
        print(f"    Lighting:   Yes")
        print(f"    Effects:    {effects}")
    else:
        print(f"    Lighting:   No")

    if device.has_logo:
        print(f"    Logo LED:   Yes")

    if device.has_scroll:
        print(f"    Scroll LED: Yes")

    if device.has_battery:
        status = "charging" if device.is_charging else "discharging"
        print(f"    Battery:    Yes ({device.battery_level}%, {status})")

    print()
    return 0


def cmd_dpi(args) -> int:
    """Set device DPI."""
    bridge = get_bridge()
    if not bridge:
        return 1

    device = find_device(bridge, args.device)
    if not device:
        print(f"Error: Device '{args.device}' not found.")
        return 1

    if not device.has_dpi:
        print(f"Error: {device.name} does not support DPI adjustment.")
        return 1

    # Parse DPI value (e.g., "800" or "800x600")
    dpi_str = args.dpi.lower()
    if "x" in dpi_str:
        parts = dpi_str.split("x")
        try:
            dpi_x, dpi_y = int(parts[0]), int(parts[1])
        except ValueError:
            print(f"Error: Invalid DPI format: {args.dpi}")
            print("Use: 800 or 800x600")
            return 1
    else:
        try:
            dpi_x = dpi_y = int(dpi_str)
        except ValueError:
            print(f"Error: Invalid DPI value: {args.dpi}")
            return 1

    # Validate range
    if not (100 <= dpi_x <= device.max_dpi and 100 <= dpi_y <= device.max_dpi):
        print(f"Error: DPI must be between 100 and {device.max_dpi}")
        return 1

    if bridge.set_dpi(device.serial, dpi_x, dpi_y):
        print(f"Set DPI to {dpi_x}x{dpi_y} on {device.name}")
        return 0
    else:
        print("Error: Failed to set DPI")
        return 1


def cmd_brightness(args) -> int:
    """Set device brightness."""
    bridge = get_bridge()
    if not bridge:
        return 1

    device = find_device(bridge, args.device)
    if not device:
        print(f"Error: Device '{args.device}' not found.")
        return 1

    if not device.has_brightness:
        print(f"Error: {device.name} does not support brightness adjustment.")
        return 1

    try:
        brightness = int(args.brightness)
    except ValueError:
        print(f"Error: Invalid brightness value: {args.brightness}")
        return 1

    if not (0 <= brightness <= 100):
        print("Error: Brightness must be between 0 and 100")
        return 1

    if bridge.set_brightness(device.serial, brightness):
        print(f"Set brightness to {brightness}% on {device.name}")
        return 0
    else:
        print("Error: Failed to set brightness")
        return 1


def cmd_poll_rate(args) -> int:
    """Set device polling rate."""
    bridge = get_bridge()
    if not bridge:
        return 1

    device = find_device(bridge, args.device)
    if not device:
        print(f"Error: Device '{args.device}' not found.")
        return 1

    if not device.has_poll_rate:
        print(f"Error: {device.name} does not support poll rate adjustment.")
        return 1

    try:
        rate = int(args.rate)
    except ValueError:
        print(f"Error: Invalid poll rate: {args.rate}")
        return 1

    if rate not in [125, 500, 1000]:
        print("Error: Poll rate must be 125, 500, or 1000 Hz")
        return 1

    if bridge.set_poll_rate(device.serial, rate):
        print(f"Set poll rate to {rate} Hz on {device.name}")
        return 0
    else:
        print("Error: Failed to set poll rate")
        return 1


def cmd_effect(args) -> int:
    """Set lighting effect."""
    bridge = get_bridge()
    if not bridge:
        return 1

    device = find_device(bridge, args.device)
    if not device:
        print(f"Error: Device '{args.device}' not found.")
        return 1

    if not device.has_lighting:
        print(f"Error: {device.name} does not support lighting.")
        return 1

    effect = args.effect.lower()

    # Check if effect is supported
    if effect not in ["off", "none"] and effect not in device.supported_effects:
        print(f"Error: Effect '{effect}' not supported by {device.name}")
        print(f"Supported effects: {', '.join(device.supported_effects)}")
        return 1

    success = False

    if effect in ["off", "none"]:
        success = bridge.set_none_effect(device.serial)
    elif effect == "spectrum":
        success = bridge.set_spectrum_effect(device.serial)
    elif effect == "breathing":
        # Use green as default, or parse color from args
        r, g, b = 0, 255, 0
        if args.color:
            color = parse_color(args.color)
            if color:
                r, g, b = color
        success = bridge.set_breathing_effect(device.serial, r, g, b)
    elif effect == "breathing_random":
        success = bridge.set_breathing_random(device.serial)
    elif effect == "wave":
        direction = WaveDirection.RIGHT
        if args.direction and args.direction.lower() == "left":
            direction = WaveDirection.LEFT
        success = bridge.set_wave_effect(device.serial, direction)
    elif effect == "reactive":
        r, g, b = 0, 255, 0
        if args.color:
            color = parse_color(args.color)
            if color:
                r, g, b = color
        speed = ReactiveSpeed.MEDIUM
        if args.speed:
            speed_map = {"short": ReactiveSpeed.SHORT, "medium": ReactiveSpeed.MEDIUM, "long": ReactiveSpeed.LONG}
            speed = speed_map.get(args.speed.lower(), ReactiveSpeed.MEDIUM)
        success = bridge.set_reactive_effect(device.serial, r, g, b, speed)
    elif effect == "starlight":
        r, g, b = 0, 255, 0
        if args.color:
            color = parse_color(args.color)
            if color:
                r, g, b = color
        success = bridge.set_starlight_effect(device.serial, r, g, b)
    elif effect == "static":
        r, g, b = 0, 255, 0
        if args.color:
            color = parse_color(args.color)
            if color:
                r, g, b = color
        success = bridge.set_static_color(device.serial, r, g, b)

    if success:
        print(f"Set effect to '{effect}' on {device.name}")
        return 0
    else:
        print(f"Error: Failed to set effect '{effect}'")
        return 1


def cmd_color(args) -> int:
    """Set static color."""
    bridge = get_bridge()
    if not bridge:
        return 1

    device = find_device(bridge, args.device)
    if not device:
        print(f"Error: Device '{args.device}' not found.")
        return 1

    if not device.has_lighting:
        print(f"Error: {device.name} does not support lighting.")
        return 1

    # Parse color
    if args.g is not None and args.b is not None:
        # Individual R G B values
        try:
            r, g, b = int(args.r), int(args.g), int(args.b)
        except ValueError:
            print("Error: RGB values must be integers 0-255")
            return 1
    else:
        # Single color string
        color = parse_color(args.r)
        if not color:
            print(f"Error: Invalid color format: {args.r}")
            print("Use: FF0000, #FF0000, or '255 0 0'")
            return 1
        r, g, b = color

    if not all(0 <= c <= 255 for c in (r, g, b)):
        print("Error: RGB values must be 0-255")
        return 1

    if bridge.set_static_color(device.serial, r, g, b):
        print(f"Set color to RGB({r}, {g}, {b}) on {device.name}")
        return 0
    else:
        print("Error: Failed to set color")
        return 1


def cmd_logo(args) -> int:
    """Control logo LED."""
    bridge = get_bridge()
    if not bridge:
        return 1

    device = find_device(bridge, args.device)
    if not device:
        print(f"Error: Device '{args.device}' not found.")
        return 1

    if not device.has_logo:
        print(f"Error: {device.name} does not have a controllable logo LED.")
        return 1

    if args.brightness is not None:
        try:
            brightness = int(args.brightness)
        except ValueError:
            print(f"Error: Invalid brightness: {args.brightness}")
            return 1

        if bridge.set_logo_brightness(device.serial, brightness):
            print(f"Set logo brightness to {brightness}% on {device.name}")
            return 0
        else:
            print("Error: Failed to set logo brightness")
            return 1

    if args.color:
        color = parse_color(args.color)
        if not color:
            print(f"Error: Invalid color: {args.color}")
            return 1
        r, g, b = color

        if bridge.set_logo_static(device.serial, r, g, b):
            print(f"Set logo color to RGB({r}, {g}, {b}) on {device.name}")
            return 0
        else:
            print("Error: Failed to set logo color")
            return 1

    print("Error: Specify --brightness or --color")
    return 1


def cmd_scroll(args) -> int:
    """Control scroll wheel LED."""
    bridge = get_bridge()
    if not bridge:
        return 1

    device = find_device(bridge, args.device)
    if not device:
        print(f"Error: Device '{args.device}' not found.")
        return 1

    if not device.has_scroll:
        print(f"Error: {device.name} does not have a controllable scroll LED.")
        return 1

    if args.brightness is not None:
        try:
            brightness = int(args.brightness)
        except ValueError:
            print(f"Error: Invalid brightness: {args.brightness}")
            return 1

        if bridge.set_scroll_brightness(device.serial, brightness):
            print(f"Set scroll brightness to {brightness}% on {device.name}")
            return 0
        else:
            print("Error: Failed to set scroll brightness")
            return 1

    if args.color:
        color = parse_color(args.color)
        if not color:
            print(f"Error: Invalid color: {args.color}")
            return 1
        r, g, b = color

        if bridge.set_scroll_static(device.serial, r, g, b):
            print(f"Set scroll color to RGB({r}, {g}, {b}) on {device.name}")
            return 0
        else:
            print("Error: Failed to set scroll color")
            return 1

    print("Error: Specify --brightness or --color")
    return 1


def main():
    parser = argparse.ArgumentParser(
        prog="razer-device",
        description="Control Razer hardware via OpenRazer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                            List all Razer devices
  %(prog)s info 0                          Show info for device #0
  %(prog)s dpi Basilisk 1600               Set DPI to 1600
  %(prog)s dpi 0 800x600                   Set DPI to 800x600
  %(prog)s brightness Basilisk 80          Set brightness to 80%%
  %(prog)s poll-rate 0 1000                Set poll rate to 1000 Hz
  %(prog)s effect Basilisk spectrum        Set spectrum effect
  %(prog)s effect 0 static --color FF0000  Set static red
  %(prog)s effect 0 wave --direction left  Set wave effect left
  %(prog)s color Basilisk 00FF00           Set color to green
  %(prog)s color 0 255 0 0                 Set color to red (RGB)
  %(prog)s logo 0 --color 00FF00           Set logo color
  %(prog)s scroll 0 --brightness 50        Set scroll brightness

Effects: static, spectrum, breathing, breathing_random, wave, reactive, starlight, off
""",
    )

    subparsers = parser.add_subparsers(dest="command", help="Command")

    # list
    sub_list = subparsers.add_parser("list", help="List all Razer devices")
    sub_list.set_defaults(func=cmd_list)

    # info
    sub_info = subparsers.add_parser("info", help="Show device information")
    sub_info.add_argument("device", help="Device serial, name, or index")
    sub_info.set_defaults(func=cmd_info)

    # dpi
    sub_dpi = subparsers.add_parser("dpi", help="Set DPI")
    sub_dpi.add_argument("device", help="Device serial, name, or index")
    sub_dpi.add_argument("dpi", help="DPI value (e.g., 800 or 800x600)")
    sub_dpi.set_defaults(func=cmd_dpi)

    # brightness
    sub_brightness = subparsers.add_parser("brightness", help="Set brightness")
    sub_brightness.add_argument("device", help="Device serial, name, or index")
    sub_brightness.add_argument("brightness", help="Brightness (0-100)")
    sub_brightness.set_defaults(func=cmd_brightness)

    # poll-rate
    sub_poll = subparsers.add_parser("poll-rate", help="Set polling rate")
    sub_poll.add_argument("device", help="Device serial, name, or index")
    sub_poll.add_argument("rate", help="Poll rate (125, 500, or 1000 Hz)")
    sub_poll.set_defaults(func=cmd_poll_rate)

    # effect
    sub_effect = subparsers.add_parser("effect", help="Set lighting effect")
    sub_effect.add_argument("device", help="Device serial, name, or index")
    sub_effect.add_argument("effect", help="Effect name (spectrum, static, breathing, wave, reactive, off)")
    sub_effect.add_argument("--color", "-c", help="Color for effect (hex or R,G,B)")
    sub_effect.add_argument("--direction", "-d", help="Direction for wave (left/right)")
    sub_effect.add_argument("--speed", "-s", help="Speed for reactive (short/medium/long)")
    sub_effect.set_defaults(func=cmd_effect)

    # color
    sub_color = subparsers.add_parser("color", help="Set static color")
    sub_color.add_argument("device", help="Device serial, name, or index")
    sub_color.add_argument("r", help="Red (0-255) or hex color")
    sub_color.add_argument("g", nargs="?", help="Green (0-255)")
    sub_color.add_argument("b", nargs="?", help="Blue (0-255)")
    sub_color.set_defaults(func=cmd_color)

    # logo
    sub_logo = subparsers.add_parser("logo", help="Control logo LED")
    sub_logo.add_argument("device", help="Device serial, name, or index")
    sub_logo.add_argument("--brightness", "-b", help="Brightness (0-100)")
    sub_logo.add_argument("--color", "-c", help="Color (hex or R,G,B)")
    sub_logo.set_defaults(func=cmd_logo)

    # scroll
    sub_scroll = subparsers.add_parser("scroll", help="Control scroll wheel LED")
    sub_scroll.add_argument("device", help="Device serial, name, or index")
    sub_scroll.add_argument("--brightness", "-b", help="Brightness (0-100)")
    sub_scroll.add_argument("--color", "-c", help="Color (hex or R,G,B)")
    sub_scroll.set_defaults(func=cmd_scroll)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
