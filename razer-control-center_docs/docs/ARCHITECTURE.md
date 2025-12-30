# Architecture

## Components

### 1) Profile Schema (data model)
- JSON profile format with:
  - layers + bindings
  - macro library
  - per-app activation matchers
  - device config sections (OpenRazer)

### 2) Remap Daemon (evdev -> uinput)
- Grabs selected physical devices (evdev)
- Interprets events using state machine (pressed keys, layer modifier)
- Emits events through a virtual device (uinput)
- Runs as **systemd --user** service
- Watches current active profile (file watch or IPC)

### 3) OpenRazer Bridge (DBus)
- Discovers Razer devices, reads capabilities
- Applies profile device settings:
  - lighting: on/off, brightness, effect, color
  - DPI stages / current stage (where supported)
  - battery polling (optional)

### 4) App Watcher (profile switching)
- Determines active application (Wayland: limited; fallback to process list)
- Chooses the most specific profile:
  - exact match -> profile
  - else global default
- Notifies remap daemon and openrazer bridge

### 5) GUI
- Device list (inputs + razer devices)
- Bindings editor (buttons/keys -> action)
- Macro editor (timeline)
- Profiles list + per-app rules
- Apply/Export/Import

## IPC
MVP: file-based + systemd restart.
Next: local socket (Unix domain) with commands:
- `set_profile <id>`
- `reload`
- `list_devices`
- `test_event_stream`

## Security/Permissions
- Access to `/dev/input/event*` required:
  - recommend udev rules to grant group `input` read access
  - avoid running as root; use group membership or ACL
- uinput access:
  - ensure `uinput` module loaded
