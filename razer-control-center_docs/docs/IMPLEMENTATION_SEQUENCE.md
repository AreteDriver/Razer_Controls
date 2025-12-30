# Implementation Sequence (do these one after the other)

## Phase 0 — MVP already built
- Repo scaffold
- Schema + example profile/macros
- OpenRazer discovery stub
- Remap daemon: Basilisk BTN_SIDE -> macro
- GUI: set BTN_SIDE -> macro + persist + systemd user service

## Phase 1 — Robust key-name mapping (must)
1. Create `crates/keycode_map/`:
   - `evdev_to_schema.py`
   - `schema_to_uinput.py`
   - include common mouse buttons and keyboard keys
2. Add validation: refuse unknown key names, show actionable error
3. Add a "test mapping" CLI command
Deliverable: mapping tables with >= 95% of common keys supported.

## Phase 2 — Stable device selection (must)
1. Build `crates/device_registry/`:
   - enumerate `/dev/input/by-id` and `/dev/input/by-path`
   - store stable identifiers in config
2. GUI: choose device(s) by stable id, not substring name
3. Remap daemon: load selected device list, retry hotplug
Deliverable: unplug/replug does not break profiles.

## Phase 3 — Multi-layer + hold-modifier layer switching
1. Implement pressed-state model:
   - track down/up for all keys
   - prevent stuck keys across layer changes
2. Implement layer rules:
   - base layer always on
   - optional hold modifier switches active layer while pressed
3. GUI: layer editor + assign hold key
Deliverable: "Hypershift" works reliably.

## Phase 4 — Per-app activation (watcher + switching)
1. Implement `services/app_watcher/`:
   - primary: process name match (psutil)
   - optional: focused window (X11 via xprop; Wayland limited)
2. Implement IPC or atomic file switch:
   - watcher writes `active_profile_id`
   - daemon reloads quickly and safely
3. GUI: add per-app rule editor
Deliverable: switching on app change in <250ms.

## Phase 5 — OpenRazer apply support (not just discovery)
1. Capability map per device:
   - lighting: brightness/effect/color
   - DPI: stages + set active stage
2. Compiler: profile -> DBus calls
3. GUI: lighting + DPI controls per device
Deliverable: change profile applies both bindings + lighting/DPI.

## Phase 6 — Macro recorder + editor
1. Record input events and translate to schema actions
2. Timeline editor in GUI:
   - reorder, edit delays, loop count
3. Safe defaults (no insane delays, bounded loops)
Deliverable: record-playback works for common workflows.

## Phase 7 — Packaging + onboarding
1. Flatpak packaging for GUI
2. systemd user units installed automatically
3. Onboarding wizard:
   - check OpenRazer daemon
   - check permissions
   - check uinput
Deliverable: new user gets working mapping in <5 minutes.
