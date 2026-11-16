#!/bin/sh
# Install z20 to ~/.local/bin and its services (presence, animate, backlight, apps) to the systemd user units.
# Usage: ./install.sh [--uleds]  (--uleds: z20 backlight as an LED too, see below)
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

# Root, once: z20 needs the keyboard's configuration interface (one hidraw node, udev/70-evga-z20.rules).
# Optional: z20 backlight's keyboard light of its own, an LED through /dev/uleds that UPower offers
# (the uleds module at boot, modules-load.d/evga-z20.conf, and udev/70-evga-z20-uleds.rules). Asked
# at a terminal when the rule is new or changed, and kept once chosen; --uleds adds it without asking.
# The commands are shown, then run with sudo if you say so; without a terminal they are only shown.
ETC=${Z20_ETC:-/etc}  # tests/test_install.py: a scratch /etc
RULE=udev/70-evga-z20.rules
ULEDS="modules-load.d/evga-z20.conf udev/70-evga-z20-uleds.rules"
target_dir() {
    case $1 in udev/*) echo "$ETC/udev/rules.d" ;; *) echo "$ETC/$(dirname "$1")" ;; esac
}
current() {
    cmp -s "$1" "$(target_dir "$1")/$(basename "$1")"
}
ask() {  # ask QUESTION DEFAULT: true for yes; an empty answer (or none) is DEFAULT, y or n
    printf '%s ' "$1"
    read -r answer || answer=
    case ${answer:-$2} in [Yy]*) return 0 ;; *) return 1 ;; esac
}

uleds=
[ -e "$ETC/modules-load.d/evga-z20.conf" ] && uleds=1  # chosen before
[ "${1:-}" = --uleds ] && uleds=1
need=
current "$RULE" || need=$RULE
if [ -z "$uleds" ] && [ -n "$need" ] && [ -t 0 ]; then
    echo
    ask "Optional: should z20 backlight also be a keyboard light that UPower offers, an LED through the
kernel's uleds module? It lets any program in your desktop session add LEDs (not change others). [y/N]" n &&
        uleds=1
fi
need_uleds=
if [ -n "$uleds" ]; then
    for f in $ULEDS; do
        current "$f" || need_uleds=1
    done
fi
[ -n "$need_uleds" ] && need="$need $ULEDS"

if [ -n "$need" ]; then
    run=
    step() {
        if [ -n "$run" ]; then "$@"; else echo "!!   $*"; fi
    }
    steps() {
        for f in $need; do
            step sudo install -m644 "$PWD/$f" "$(target_dir "$f")/"
        done
        step sudo udevadm control --reload
        if [ -n "$need_uleds" ]; then
            step sudo modprobe uleds
            step sudo udevadm trigger --subsystem-match=hidraw --subsystem-match=misc --action=change
        else
            step sudo udevadm trigger --subsystem-match=hidraw --action=change
        fi
    }
    echo
    echo "!! As root, once (or unplug and replug the keyboard instead of the trigger):"
    steps
    if [ -t 0 ] && ask "Run these now with sudo? [Y/n]" y; then
        run=1
        steps
        echo "Done: the keyboard's configuration interface is yours while you are logged in."
    fi
    echo
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
