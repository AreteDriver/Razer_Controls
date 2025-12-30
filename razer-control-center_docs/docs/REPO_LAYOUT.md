# Target Repo Layout

```
razer-control-center/
  apps/
    gui/                     # GUI (PySide6 or Tauri/Qt; MVP uses PySide6)
  services/
    remap_daemon/            # evdev->uinput remap engine + profile watcher
    openrazer_bridge/        # DBus discovery + apply config
    app_watcher/             # per-app profile switching (focus/process)
  crates/
    profile_schema/          # schema + migrations + validation
    device_registry/         # stable device IDs, udev mapping, capabilities cache
    keycode_map/             # evdev<->schema<->uinput mapping tables
  packaging/
    systemd/
    flatpak/
  docs/
```

## Core separation
- **OpenRazer plane**: lighting/DPI/battery (device capabilities)
- **Remap plane**: buttons/keys/macros/layers (input behavior)
- **Profile compiler**: converts schema -> backend actions
