# Claude Code Prompts (run in order)

## Prompt 1 — Upgrade key mapping tables
You are a senior Linux input developer. Implement `crates/keycode_map/` with:
- evdev code -> schema key name mapping
- schema key name -> uinput constant mapping
- include mouse: BTN_LEFT/RIGHT/MIDDLE/SIDE/EXTRA, wheel clicks
- include keyboard: letters, numbers, F1-F24, modifiers, arrows, media keys
Add a CLI tool `python -m tools.keymap_check --list` and `--validate <profile.json>`.
Do not break existing MVP. Add unit tests.

## Prompt 2 — Stable device registry
Implement `crates/device_registry/`:
- enumerate input devices with stable IDs from `/dev/input/by-id` and `/dev/input/by-path`
- store selected devices in `~/.config/razer-control-center/devices.json`
Update remap daemon to load device selections by stable id and handle hotplug.
Update GUI to let user select devices and persist selection.
Add diagnostics view: show currently grabbed devices.

## Prompt 3 — Layer switching engine
Implement a proper event state machine in `services/remap_daemon/`:
- pressed key tracking
- layer activation via hold modifier (`Layer.hold_modifier_input_code`)
- guarantee no stuck keys
- allow bindings to output: key chord, macro, or passthrough
Add integration tests using synthetic events.

## Prompt 4 — App watcher + fast switching
Implement `services/app_watcher/`:
- monitor running processes and determine the "active" app for profile switching
- support `Profile.match_process_names`
Implement IPC using Unix domain socket:
- watcher sends `set_profile <id>`
- daemon acks and reloads bindings without restart
GUI: allow per-app rules.

## Prompt 5 — OpenRazer apply bridge
Implement `services/openrazer_bridge/`:
- reliable discovery of device objects via DBus introspection
- a normalized capability layer
- apply: lighting + DPI from profile.devices[device_id]
Add CLI: `python -m tools.openrazer_apply --profile <id>`
GUI: add device settings page.

## Prompt 6 — Packaging + onboarding
Create `packaging/flatpak/` and improve systemd user service installs.
Implement onboarding wizard in GUI:
- detect openrazer-daemon status
- detect input permissions and offer udev rule instructions
- detect uinput module and show fix steps
Ensure "Apply on login" works.
