#!/bin/sh
# Removes what install.sh installed for the current user: z20, the settings app and its menu entry,
# the user services (stopped and disabled first). Keeps the settings (~/.config/z20) and the backups
# (~/.local/state/z20), and says how to remove the udev rules and the uleds entry, which take root.
set -eu
UNITS="z20-presence.service z20-animate.service z20-backlight.service z20-apps.service"

if command -v systemctl >/dev/null 2>&1; then
    # shellcheck disable=SC2086
    systemctl --user disable --now $UNITS 2>/dev/null || true
fi
rm -f ~/.local/bin/z20 ~/.local/bin/z20-settings ~/.local/share/applications/de.thokas.z20-settings.desktop
for unit in $UNITS; do
    rm -f ~/.config/systemd/user/"$unit"
done
rm -rf ~/.local/share/z20
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload || true
fi

echo "Removed z20, z20-settings and the z20 user services."
if [ -e /etc/udev/rules.d/70-evga-z20.rules ] || [ -e /etc/udev/rules.d/70-evga-z20-uleds.rules ] ||
        [ -e /etc/modules-load.d/evga-z20.conf ]; then
    cat <<'MSG'
!! The udev rules and the uleds module's entry need root to remove:
!!   sudo rm -f /etc/udev/rules.d/70-evga-z20.rules /etc/udev/rules.d/70-evga-z20-uleds.rules \
!!       /etc/modules-load.d/evga-z20.conf
!!   sudo udevadm control --reload
MSG
fi
cat <<'MSG'
Kept your settings (~/.config/z20) and backups (~/.local/state/z20); remove them too with
  rm -r ~/.config/z20 ~/.local/state/z20
MSG
