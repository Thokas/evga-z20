#!/bin/sh
# Install z20 to ~/.local/bin and its presence service to the systemd user units.
# Re-run after updating.
set -eu
cd "$(dirname "$0")"

install -Dm755 z20 ~/.local/bin/z20
install -Dm644 systemd/z20-presence.service ~/.config/systemd/user/z20-presence.service
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload || true
    systemctl --user try-restart z20-presence.service || true  # a running service picks up the new z20
fi

# z20 needs the keyboard's configuration interface (one hidraw node); that takes root once.
if ! cmp -s udev/70-evga-z20.rules /etc/udev/rules.d/70-evga-z20.rules; then
    cat <<MSG
!! Install the udev rule once (as root), then unplug and replug the keyboard or run the trigger:
!!   sudo install -m644 $PWD/udev/70-evga-z20.rules /etc/udev/rules.d/
!!   sudo udevadm control --reload && sudo udevadm trigger --subsystem-match=hidraw --action=change

MSG
fi

cat <<'MSG'
Installed ~/.local/bin/z20. Try: z20 status
To act on the desktop when you leave and come back (settings: ~/.config/z20/presence.ini):
  systemctl --user enable --now z20-presence.service
MSG
