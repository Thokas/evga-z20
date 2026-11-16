#!/bin/sh
# Install z20 to ~/.local/bin and its services (presence, animate, backlight, apps) to the systemd user units.
# Re-run after updating.
set -eu
cd "$(dirname "$0")"

install -Dm755 z20 ~/.local/bin/z20
# The settings app: its launcher, its QML (which the Plasma widget's install copies its shared part from)
# and its menu entry, which starts it by its full path (~/.local/bin isn't always on a menu's PATH).
install -Dm755 app/z20-settings ~/.local/bin/z20-settings
rm -rf ~/.local/share/z20/app
mkdir -p ~/.local/share/z20/app ~/.local/share/applications
cp -r app/qml ~/.local/share/z20/app/
sed "s|^Exec=z20-settings|Exec=$HOME/.local/bin/z20-settings|" app/de.thokas.z20-settings.desktop \
    > ~/.local/share/applications/de.thokas.z20-settings.desktop
for unit in z20-presence.service z20-animate.service z20-backlight.service z20-apps.service; do
    install -Dm644 "systemd/$unit" ~/.config/systemd/user/"$unit"
done
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user daemon-reload || true
    # running services pick up the new z20
    systemctl --user try-restart z20-presence.service z20-animate.service z20-backlight.service \
        z20-apps.service || true
fi

# z20 needs the keyboard's configuration interface (one hidraw node), and z20 backlight /dev/uleds
# for a keyboard light of its own; that takes root once.
if ! cmp -s udev/70-evga-z20.rules /etc/udev/rules.d/70-evga-z20.rules ||
        ! cmp -s modules-load.d/evga-z20.conf /etc/modules-load.d/evga-z20.conf; then
    cat <<MSG
!! Install the udev rule and the uleds module's entry once (as root), then unplug and replug the
!! keyboard or run the trigger:
!!   sudo install -m644 $PWD/udev/70-evga-z20.rules /etc/udev/rules.d/
!!   sudo install -m644 $PWD/modules-load.d/evga-z20.conf /etc/modules-load.d/
!!   sudo udevadm control --reload && sudo modprobe uleds
!!   sudo udevadm trigger --subsystem-match=hidraw --subsystem-match=misc --action=change

MSG
fi

cat <<'MSG'
Installed ~/.local/bin/z20. Try: z20 status
To act on the desktop when you leave and come back (settings: ~/.config/z20/presence.ini):
  systemctl --user enable --now z20-presence.service
Software effects over the lighting, also after the next login: z20 animate fire --save
The Z20's own keyboard light, dark while the desktop's is off (the z20-backlight service): z20 backlight 60
A profile while a program runs (rules: ~/.config/z20/apps.ini): z20 apps add Cyberpunk2077.exe 3; z20 apps on
The settings in a window (lighting presets, macros, profiles, programs, presence): z20-settings
MSG
