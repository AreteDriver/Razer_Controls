#!/bin/bash
# Fix permissions for Razer Control Center remap daemon

set -e

echo "=== Fixing Razer Control Center Permissions ==="
echo

# 1. Load uinput module
echo "Loading uinput module..."
sudo modprobe uinput
echo "  ✓ uinput loaded"

# 2. Add user to input group
echo
echo "Adding $USER to input group..."
sudo usermod -aG input "$USER"
echo "  ✓ Added to input group"

# 3. Create udev rule for uinput
echo
echo "Creating udev rule for uinput..."
echo 'KERNEL=="uinput", MODE="0660", GROUP="input", OPTIONS+="static_node=uinput"' | sudo tee /etc/udev/rules.d/99-razer-controls.rules > /dev/null
echo "  ✓ udev rule created"

# 4. Reload udev
echo
echo "Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger
echo "  ✓ udev reloaded"

# 5. Apply group now (for current session)
echo
echo "=== IMPORTANT ==="
echo "You need to LOG OUT and LOG BACK IN for group changes to take effect."
echo
echo "Or run this command to apply immediately (new shell only):"
echo "  newgrp input"
echo
echo "Then restart the daemon:"
echo "  systemctl --user restart razer-remap-daemon"
