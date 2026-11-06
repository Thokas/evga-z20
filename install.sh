#!/bin/sh
# Install z20 to ~/.local/bin and its services (presence, animate) to the systemd user units.
# Re-run after updating.
set -eu
cd "$(dirname "$0")"

install -Dm755 z20 ~/.local/bin/z20
for unit in z20-presence.service z20-animate.service; do
    install -Dm644 "systemd/$unit" ~/.config/systemd/user/"$unit"
done
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload || true
    # running services pick up the new z20
    systemctl --user try-restart z20-presence.service z20-animate.service || true
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
Software effects over the lighting, also after the next login: z20 animate fire --save
MSG
