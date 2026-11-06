#!/bin/sh
# Install z20 to ~/.local/bin. Re-run after updating.
set -eu
cd "$(dirname "$0")"

install -Dm755 z20 ~/.local/bin/z20

# z20 needs the keyboard's configuration interface (one hidraw node); that takes root once.
if ! cmp -s udev/70-evga-z20.rules /etc/udev/rules.d/70-evga-z20.rules; then
    cat <<MSG
!! Install the udev rule once (as root), then unplug and replug the keyboard or run the trigger:
!!   sudo install -m644 $PWD/udev/70-evga-z20.rules /etc/udev/rules.d/
!!   sudo udevadm control --reload && sudo udevadm trigger --subsystem-match=hidraw --action=change

MSG
fi

echo "Installed ~/.local/bin/z20. Try: z20 status"
