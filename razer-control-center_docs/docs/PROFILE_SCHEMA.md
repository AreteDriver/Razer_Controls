# Profile Schema

## Goals
- Backend-agnostic "intent" format
- Easy to diff/merge in Git
- Supports:
  - multi-layer bindings
  - hold-to-shift layer ("Hypershift")
  - macros (chords, delays, text)
  - per-app auto-switching
  - device configs for OpenRazer

## Files
- `~/.config/razer-control-center/profiles/*.json`
- `~/.config/razer-control-center/macros.json`
- optional: `devices.json` cache (stable IDs)

## Canonical model
Generate `crates/profile_schema/schema.py` from MVP, then evolve.

## Event naming
Use a string namespace:
- evdev codes: `BTN_SIDE`, `BTN_EXTRA`, `KEY_F13`, etc.
- schema keys: `CTRL`, `SHIFT`, etc. (compiler maps to uinput)
