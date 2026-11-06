# evga-z20

**evga-z20** sets up EVGA Z20 keyboards (Z20 and Z20 Elite, ANSI and ISO) on
Linux, without EVGA's Windows software. It is a single Python file with no
dependencies, and it talks to the keyboard's configuration interface over
hidraw.

- **Lighting per profile:** off, static, breathing, wave, spiral, pulse,
  stars, reactive and more, with color, brightness and speed
- **Live lighting:** the same effects in RAM only (for scripts and widgets,
  without wearing the flash), and colors per key, light bar LED and logo
- **Profiles and Game Mode:** switch profiles 1–9, turn Game Mode on or off
- **Backup and restore** of all nine profiles and the stored macros
- **Keys:** see and change what any key does, also the macro keys E1–E5 and
  the Fn layer (a stored macro once, N times, toggled or held; a key
  combination, media key, click, profile); back to the factory setting one
  by one or all at once
- **Macros:** list them step by step; create, edit, rename and delete them
- **Presence sensor:** its settings per profile (distance, what happens when
  you come and go, welcome effect) and the live distance; a service that
  locks the screen, pauses media and the like each time you leave and come
  back
- **JSON output** for widgets and scripts

Before every change it saves what it replaces, and after the write it reads
it back to check it. It never sends firmware, reset or factory-reset
commands. [PROTOCOL.md](PROTOCOL.md) documents the configuration protocol,
which was worked out from Unleash RGB for interoperability. Tested on a Z20
Elite ISO (firmware 1.38).

> [!WARNING]
> **Written entirely by AI.** This project is "vibe-coded": the code, the
> tests, the protocol notes and this README were written by an AI assistant
> (Claude, in Claude Code) from a person's prompts, and checked by trying
> them on one keyboard, not by a person reading every line. The protocol was
> worked out the same way. It works on the keyboard it was tried on; read
> the code before you trust it with yours, keep `z20 backup` copies, and use
> it at your own risk.

## Keyboards

| USB ID      | Model                | |
| ----------- | -------------------- | --- |
| `3842:2610` | Z20 Elite, ISO layout | tested, firmware 1.38 |
| `3842:260a` | Z20 Elite            | untested |
| `3842:260c` | Z20 RGB              | untested |
| `3842:2617` | Z20 RGB, ISO layout  | untested |

EVGA's software drives all four with the same code, so they should work;
please report how yours does (`lsusb | grep 3842` shows the ID). The Z20
TKL, Z15 and Z12 use other code and aren't supported.

## Use

```
z20 status [--json]                   profile, Game Mode, lighting, E1-E5, macro names
z20 macros [--json]                   stored macros, step by step
z20 macro new Hi "LShift down, H, LShift up, I"
                                      store a macro in a free slot (prints its number)
z20 macro edit 5 "ctrl down, c, ctrl up" | rename 5 Copy | delete 5
z20 profile N                         switch to profile 1-9 (also Fn + 1-9)
z20 game-mode on | off | toggle
z20 key E4                            what macro key E4 does (or capslock, f1, a, game ...)
z20 key E4 macro 2                    run macro 2 once (z20 macros lists them)
z20 key E4 macro 2 --repeat 3 | --toggle | --hold
                                      3 times, until E4 is pressed again, while E4 is held
z20 key capslock key lctrl            or: key ctrl+shift+t, media playpause, click left,
                                      wheel up, profile 2, off, default (factory setting)
z20 key all default                   every key as from the factory, E1-E5 too (not Win, Fn)
z20 key ... --fn | --profile N        the key's Fn layer, another profile
z20 light [--json]                    lighting of the active profile
z20 light off
z20 light static ff8000               one color (rrggbb or #rrggbb)
z20 light breathing 00ff00 [0000ff]   breathe between two colors (or into dark)
z20 light wave | spiral | pulse | stars | reactive | fade | rows
                                      that effect, with the colors the profile keeps for it
z20 light ... --profile N             another profile than the active one
z20 light ... --brightness P          percent, for the effect's colors
z20 light ... --cycle MS              length of one effect cycle (speed)
z20 light static 0000ff --live        only in RAM: until reload, profile switch, unplugging
z20 light reload                      back to the stored lighting
z20 color all 000000 w,a,s,d ff0000   colors per LED over the lighting (later calls add);
                                      also e1, LeftBar1-9, RightBar1-9, Logo1-4, keys, bars, logo
z20 color off                         back to the profile's lighting
z20 sensor [--json]                   presence sensor settings and the distance now
z20 sensor watch                      distance, present / away and keyboard events, live
z20 sensor on | off | distance 45     present: closer than 45 cm (10-120)
z20 sensor leave dark 30              when you leave, after 30 s: dark, lock, sleep, nothing
z20 sensor come wake 1                when you come, after 1 s: wake, unlock, nothing
z20 sensor welcome thunder 3000       effect when you come (fade, rows, explosion, raining,
                                      barber, lightbar, thunder) and its length in ms
z20 presence [--dry-run]              lock, pause media, screen off ... when you leave
                                      (a service, see Presence service)
z20 backup                            profiles 1-9 and macros to ~/.local/state/z20/backups/
z20 restore DIR [--profile N | --macro N]
                                      write profiles and macros back from a backup
```

```
$ z20 status
EVGA Z20 Elite ISO, firmware 1.38: profile 1 "DEFAULT 1", Game Mode off, NKRO
lighting: wave 3000 ms
E1      macro 1 "Autorunner" (loop until pressed again)
E2      left click
E3      macro 3 "Autoclick" (loop until pressed again)
E4      disabled
E5      disabled
macros on no key: 2 "New Macro", 4 "Laugh"
```

`status` also lists every other key that does something else than from the
factory.

Keys are named as on a US keyboard, because a key function belongs to a
place on the keyboard: on a German one, `z20 key y` is the key printed "Z".
The names are the ones `z20 macros` uses (`A`, `F1`, `CapsLock`, `Comma`,
`KPPlus`, `LShift`, ...), plus `E1`-`E5`, `Game` (the Game Mode key),
`PlayPause`, `WheelUp` / `WheelDown` (the volume wheel) and `Mute`; signs
can also be written as words (`grave`, `minus`, `semicolon`, `slash`, ...).
Fn itself stays Fn, and the Fn layer of 1-0, F12, Alt and the arrow keys
stays the keyboard's own (profiles, brightness, recording macros), as in
Unleash.

Lighting belongs to a profile: each of the nine profiles has its own effect
and keeps settings for every effect, so `z20 light wave` switches back to the
wave as it was set up (in Unleash or with the keyboard's Fn keys). `--json`
output is meant for widgets and scripts.

`z20 light` writes the profile to the keyboard's flash. For changes that
come often (a widget, dimming when idle, showing a state) use `--live`: it
changes only the RAM copy of the active profile, and `z20 light reload`,
switching profiles or unplugging bring back what is stored. `z20 light`
shows what is on and, after `--live`, what is stored. `z20 color` puts
colors on single LEDs over whatever lighting runs, until `z20 color off`;
it keeps the colors in `~/.local/state/z20/colors.bin`, so each call adds to
the last one (`all 000000` starts from dark). The keyboard doesn't store
them.

Macro steps are written the way `z20 macros` prints them, separated by
commas: `KEY down`, `KEY up`, `wait 20 ms`, `left button down`, `wheel up`,
`playpause down`, `mouse to X Y`. A key, `left click` or media key on its
own is pressed and let go. Keys go by the names `z20 macros` shows (`A`,
`LShift`, `Enter`, `F14`, `Comma`, ...); they are positions on the keyboard,
so the layout set on the computer decides the character (Z gives "y" on a
German layout). Every step gets a short wait before it (2.5 ms if none is
given, as Unleash does): steps without one would merge, and a key pressed and
let go in the same instant never shows. Add longer waits for programs that
miss fast input. The run mode (once, N times, toggled, held) belongs to the
key: `z20 key E4 macro 5 --repeat 3`.

The presence sensor on top of the keyboard measures the distance to what is
in front of it. Each profile says within which distance someone counts as
present, what the keyboard does a few seconds after you leave (the lighting
goes dark, by default) and when you come back (a welcome effect). The
factory distance, 120 cm, can be too far: a chair half a metre away keeps
the keyboard "occupied". `z20 sensor watch` shows what the sensor measures
while you sit, lean back and walk away; set the distance between your
sitting and your empty-desk values (`z20 sensor distance 45`). The keyboard
reports nothing to the computer when you come or go; `watch` reads the
distance twice a second. `leave lock` works on KDE: the keyboard types
Win+L, which KDE takes as Meta+L and locks the screen. But the keyboard
does its leave action only once after being plugged in or after a sensor
change; the next time you leave, nothing happens. The sleep, wake and
unlock actions are meant for Windows and haven't been tried on Linux: sleep
may suspend the computer.

### Presence service

`z20 presence` watches the sensor and acts on the desktop each time you
leave and come back. It runs as a systemd user service:

```
systemctl --user enable --now z20-presence.service
journalctl --user -u z20-presence -f          # what it does
z20 presence --dry-run                        # try: says what it would do
```

Settings in `~/.config/z20/presence.ini`, all optional:

```ini
[presence]
# present when closer than this (cm); default: the active profile's sensor distance
distance = 45
# seconds away before "leave" runs, seconds near again before "come" runs
leave after = 30
come after = 1
# actions: lock, screen-off, wake, pause-media, resume-media; each may wait
# "after SECONDS" from the moment the service saw you leave or come back
leave = lock, pause-media, screen-off after 60
come = wake, resume-media
# and a command of your own, if you like
leave run = notify-send "z20" "see you"
```

`lock` is `loginctl lock-session`; `screen-off` and `wake` use KDE's
`kscreen-doctor` and the screen saver's `SimulateUserActivity`;
`pause-media` pauses the media players that are playing (MPRIS) and
`resume-media` starts only those again. Coming back drops what leaving
still had waiting (no screen-off after you sat down again), and the other
way round. Without a config file: leave =
`pause-media`, come = `wake, resume-media`. It reads the distance twice a
second and decides on the median of the last five readings (single ones
jump by a few centimetres), keeps waiting while the keyboard is unplugged
or the computer sleeps, and lets other `z20` commands run in between.

The sensor sees the nearest thing in front of it: a chair left near the
distance you set looks like someone leaning back. Push the chair back or
turn it aside when you leave, or set `distance` a little shorter than
where the empty chair stands (`z20 sensor watch` shows both). The keyboard's
own leave action wants even more room: it didn't act with the empty chair
at 46-51 cm and the distance at 45 cm, only from about 70 cm on.

To use E1-E5 as desktop shortcuts, give them keys no keyboard has, like
`z20 key E4 key f14`, and bind those in the desktop's shortcut settings.
F13-F18 are free; avoid F20-F23, which X keyboard maps turn into mic mute
and touchpad on / off / toggle.

## Install

```
git clone https://github.com/Thokas/evga-z20.git && cd evga-z20
./install.sh                     # z20 to ~/.local/bin
# once, as root: let the logged-in user reach the keyboard's configuration interface
sudo install -m644 udev/70-evga-z20.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger --subsystem-match=hidraw --action=change
z20 backup                       # keep a copy of how the keyboard is set up now
```

Needs Python 3.8 or newer and a desktop session with systemd-logind (the rule
uses `uaccess`). The rule opens only USB interface 1, which carries the
configuration reports; the two interfaces that carry your keystrokes stay
root-only.

## Safety

- `z20` only sends commands from a fixed list and refuses anything else. The
  keyboard also knows reset, erase firmware, bootloader and factory reset
  commands: those never go out (`tests/` checks this).
- Before a profile or macro is written, what it replaces goes to
  `~/.local/state/z20/previous/`; afterwards it is read back and compared.
  `z20 restore ~/.local/state/z20/previous` undoes the last change.
- `z20 key` changes only the key you name; `z20 macro delete` refuses a
  macro that a key in any profile still runs.
- The firmware is never touched; leave updates to Unleash RGB.
- Backups and `previous/` are readable by you only: macros can hold
  anything that was typed while recording them.
- One `z20` at a time: a second one (say, a widget polling while you change
  the lighting) waits, and every answer is checked to belong to its request.

What the udev rule allows: any program running as you in your desktop
session can send the keyboard's configuration interface anything, including
the commands `z20` refuses. It can change lighting, keys and macros, put the
keyboard into its bootloader or erase its firmware (Unleash RGB on Windows
can flash it again). It cannot flash new firmware, because the bootloader
appears as another USB device that the rule doesn't open. Changed keys and
macros stay in the keyboard, also on other computers, so check with
`z20 status` if something types on its own. Chrome and other Chromium
browsers can reach the interface through WebHID, but only after you pick the
keyboard in the browser's device chooser: don't allow a website "EVGA Z20".
Without the rule, `z20` works only as root.

## How it works

The keyboard's configuration interface takes commands as HID feature
reports and answers each in the same report, read back right after. A
profile (name, key functions, lighting) is one 1806-byte report; `z20`
changes a profile the way Unleash does: read it, change only the bytes that
matter, write it back with a new checksum. For the active profile it then
puts the changed parts into the keyboard's RAM (lighting blocks, sensor
settings, single keys), so they work at once without a reload: a reload
restarts the lighting effect, and one set to start on a key press would
stay dark until then. The details are in [PROTOCOL.md](PROTOCOL.md).

Tests (offline, no keyboard needed): `python3 -I -m unittest discover -s tests`

## Not done yet

- What the presence sensor's sleep, wake and unlock actions send, and its 4
  gesture slots.
- The brightness set with Fn + Up / Down: where the keyboard keeps it isn't
  known yet.

## Uninstall

```
rm ~/.local/bin/z20
sudo rm /etc/udev/rules.d/70-evga-z20.rules
rm -r ~/.local/state/z20         # the backups too
```

## Note

Not made or endorsed by EVGA. The protocol was worked out from EVGA's
Unleash RGB 1.0.28 for interoperability; this repository contains none of
EVGA's code or files.

## License

MIT, see [LICENSE](LICENSE). The code and documentation were written by AI
(see the note at the top); the facts about the protocol in PROTOCOL.md are
free for anyone to use.
