# Razer Control Center for Linux — Document Collection (for Claude Code)

This folder is a build-ready specification and implementation plan for a "Synapse-like" Linux experience:
- One GUI for all Razer devices
- Profiles, per-app switching
- Button/key remapping + macros + layers (Wayland-safe)
- OpenRazer integration for device features (RGB/DPI/battery/etc.)
- Systemd user services for persistence

## Intended outcomes
- Reliable remapping under Wayland/X11 via evdev->uinput
- Clean separation between "hardware capabilities" and "input behavior"
- A single profile schema compiled to backend actions

## How to use with Claude Code
Start with `docs/CLAUDE_CODE_PROMPTS.md`. Run prompts in order.

## Repo layout (target)
See `docs/REPO_LAYOUT.md`.
