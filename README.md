# evga-z20

**evga-z20** sets up EVGA Z20 keyboards (Z20 and Z20 Elite, ANSI and ISO) on
Linux, without EVGA's Windows software. It is a single Python file with no
dependencies, and it talks to the keyboard's configuration interface over
hidraw.

- **Lighting per profile:** off, static, breathing, wave, spiral, pulse,
  stars, reactive and more, with color, brightness and speed
- **Live lighting:** the same effects in RAM only (for scripts and widgets,
  without wearing the flash), and colors per key, light bar LED and logo
- **Software effects:** aurora, fire, rain, ripple, scanner and a color
  gradient, worked out by `z20` and sent 25 times a second over the lighting,
  as a user service that also starts after login
- **Keyboard light:** a brightness of the Z20's own, dark while KDE Plasma
  has its keyboard light off (when the screen dims or goes off), as a user
  service; also an LED that UPower offers as a keyboard light
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
- **Profiles for programs:** while a game or other program runs, the
  keyboard is on its profile, and back on the one from before when it ends
  (a user service; Unleash RGB 1.0.28 has nothing like it)
- **Settings app** (`z20-settings`): lighting presets on a drawing of the
  keyboard with colors per key, macros, profile names, profiles for
  programs, presence and the keyboard's own settings, in a window
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
z20 profile [--json]                  the profiles 1-9 with their names
z20 profile N                         switch to profile 1-9 (also Fn + 1-9)
z20 profile rename 2 Games | copy 1 2 rename a profile; copy profile 1's settings into 2
z20 rate [1000 | 2000 | 4000]         report rate (Hz) of the active profile
z20 nkro on | off                     n-key rollover, or 6 keys at a time
z20 game-mode keys win,alt-tab        the keys Game Mode blocks (also menu, lshift, alt-f4,
                                      ctrl-esc, tab; none)
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
z20 light static ff8000               one color (rrggbb or #rrggbb; without: the stored one)
z20 light breathing 00ff00 [0000ff]   breathe between two colors (or into dark)
z20 light wave | spiral | pulse | stars | reactive | fade | rows
                                      that effect, with the colors the profile keeps for it
z20 light wave 0040ff 00e0ff --direction left
                                      or with your own colors (repeated to fill its 7-8);
                                      wave: up, down, left, right; spiral: cw, ccw
z20 light ... --profile N             another profile than the active one
z20 light ... --brightness P          percent, for the effect's colors
z20 light ... --cycle MS              length of one effect cycle (speed)
z20 light static 0000ff --live        only in RAM: until reload, profile switch, unplugging
z20 light reload                      back to the stored lighting
z20 light default | sensor default    back to the factory setting
z20 color all 000000 w,a,s,d ff0000   colors per LED over the lighting (later calls add);
                                      also e1, LeftBar1-9, RightBar1-9, Logo1-4, keys, bars, logo
z20 color all none w ff0000 --live    for now (none: the lighting shows); z20 color reload
z20 color off                         back to the profile's lighting
z20 leds --json                       every LED with its name, place and key size
z20 animate fire                      a software effect, until Ctrl+C: aurora, fire, rain,
                                      ripple, scanner, gradient [COLOR ...] [--cycle MS]
                                      [--brightness P]
z20 animate fire --save | --live      as the z20-animate service: also after login, or for now
z20 animate off | reload | --json     stop it; back to the saved one; what runs
z20 backlight 60 | up | down          the Z20's own keyboard light, dark while the desktop
                                      has its off (a service, see Keyboard light)
z20 sensor [--json]                   presence sensor settings and the distance now
z20 sensor watch                      distance, present / away and keyboard events, live
z20 sensor on | off | distance 45     present: closer than 45 cm (10-120)
z20 sensor leave dark 30              when you leave, after 30 s: dark, lock, sleep, nothing
z20 sensor come wake 1                when you come, after 1 s: wake, unlock, nothing
z20 sensor welcome thunder 3000       effect when you come (fade, rows, explosion, raining,
                                      barber, lightbar, thunder) and its length in ms
z20 events [--json] [--wait S]        what the keyboard reports itself (profile, effect and
                                      Game Mode changed with its keys, media keys); with
                                      --wait only the first event within S seconds,
                                      media keys left out
z20 presence [--dry-run]              lock, pause media, screen off ... when you leave
z20 presence settings [--json]        what it does: presence.ini with its defaults
                                      (a service, see Presence service)
z20 presence set KEY VALUE ...        change presence.ini, like
                                      z20 presence set leave "" away-light "animate fire"
z20 apps [--json]                     profiles for programs: the rules, and which applies now
z20 apps add Cyberpunk2077.exe 3      while it runs, profile 3; when it ends, the one from
                                      before (a service, see Profiles for programs)
z20 apps remove PROGRAM | set ...     a rule less; all of them, in a new order
z20 apps on | off                     the service that switches
z20 apps running [--json]             what runs now, newest first, to name in a rule
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
the last one (`all 000000` starts from dark, `all none` from none). The
keyboard doesn't store them. With `--live` they are only for now, kept apart
until `z20 color reload` brings back the stored ones; `z20 animate` draws
them over its frames. `z20 leds` lists every LED with its place and key size,
for drawing the keyboard.

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

### Software effects

Beyond its own effects, the keyboard shows any colors per LED that it is
sent. `z20 animate` works out every LED's color and sends a frame 25 times a
second, as Unleash does for its custom effects. Working out a frame takes
well under a millisecond; sending it holds the keyboard for a few
milliseconds, so other `z20` commands (and the widget) go on in between.

```
z20 animate aurora                       flowing color fields (default: green, blue, violet)
z20 animate fire                         flames from the bottom row (colors: embers to tips)
z20 animate rain 00ff40 c0ffc0           drops falling down the columns (trail, drop)
z20 animate ripple ff0000 0000ff         rings spreading from random keys
z20 animate scanner ff0000 --cycle 1500  a light running from side to side
z20 animate gradient ff0080 0080ff       a still gradient from left to right
z20 animate fire --save                  run it as the z20-animate user service, also after login
z20 animate off                          stop it: the profile's lighting shows again
```

The effects use a map of where each LED sits (keys in key widths, the light
bars at the sides), ISO or ANSI as the keyboard is. They pause while the
screen is locked (the keyboard's own lighting shows then) and while the
keyboard is unplugged. One runs at a time; a new one replaces the last.
It says when it pauses and when a frame comes late, and why (in the
service: `journalctl --user -u z20-animate`).
`--save` keeps the effect in `~/.config/z20/animation.ini` and enables the
`z20-animate` service; `--live` runs it in the service only until
`z20 animate reload` (back to the saved one) or logging out. While one
runs, `z20 light` changes the lighting underneath it.

### Keyboard light

The Z20 has a keyboard light of its own: a level, in percent of how the
lighting is set, that the `z20-backlight` user service keeps. It goes along
with the desktop's keyboard light: its slider sets it too, and when KDE
Plasma dims the screens while you're away, the Z20 dims as much (to 30 % of
its level); when it turns them off, or its keyboard light is switched off
otherwise (its slider at 0), the Z20 is dark. It comes back with the
screens.

```
z20 backlight 60                              the Z20 at 60 % (enables the service)
z20 backlight up | down                       10 % more or less, for a shortcut
z20 backlight [--json]                        the level, and whether the service runs
journalctl --user -u z20-backlight -f         what it does
```

The EVGA Z20 widget has a slider for it. It dims the keyboard's own
lighting in RAM only, never what is stored (`z20 light` shows the lighting
as set, and "dimmed to 60 %"), software effects (which pause while it's
dark) and the colors of `z20 color`. Changes while it dims, with `z20` or
the keyboard's Fn keys, are dimmed as well. Stopped, the service leaves the
lighting as it is set. The keyboard's own brightness (Fn + Up / Down) comes
on top.

With the optional `uleds` module and its udev rule (see Install), the
level is also an LED of its own, `evga_z20::kbd_backlight`, which UPower offers as a
keyboard light next to a laptop's. Whatever sets UPower's keyboard lights
can set it:

```
busctl --system call org.freedesktop.UPower /org/freedesktop/UPower/KbdBacklight/evga_z20ookbd_backlight \
    org.freedesktop.UPower.KbdBacklight SetBrightness i 40
```

Plasma 6.6 shows only one keyboard light, UPower's first: a laptop's own.
From UPower 1.91.4 on, that one sets all keyboard lights at once, so there
Plasma's slider moves the Z20 as well. Without the LED, `z20 backlight` works
the same, only UPower doesn't know it.

Plasma's keyboard slider (a laptop's light) sets the Z20 as well: low is
50 %, high 100 % with a ThinkPad's three steps. Whichever slider you moved
last counts; Plasma bringing its light back after dimming, the lid or a
suspend doesn't undo the Z20's own. z20 takes what the desktop sets, not
what the laptop does itself: a laptop's own key for its light leaves the
Z20 alone.
Plasma only turns its keyboard light off, also when it dims the screens, so
z20 then asks `kscreen-doctor` how far the screens are dimmed and whether
they are off (elsewhere, off is off).
Plasma also turns its keyboard light off when the lid closes (for the
laptop's own keys, even with screens attached), and again each time it loads
a power profile while the lid is closed (settings saved, the power cable
plugged in or out); the Z20 stays lit then.
Plasma turns its keyboard light off when idle only if it is on, so with a
laptop's light switched off by its own key, the Z20 stays lit when the screen
dims. On a desktop computer without a keyboard light, Plasma has none to turn
off. Dark with the desktop's keyboard light also means dark for a presence
`away light`.

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
# the keyboard's lighting while you are away, as for z20 light or z20 animate
away light = animate scanner ff0000 --cycle 2000
```

To only light the keyboard when you leave, without locking anything:

```
z20 presence set leave "" away-light "light breathing ff0000 000000"
```

`z20 presence set` changes the settings it names and leaves the rest of the
file, comments too, as it is; it restarts the service if it runs. An empty
`leave` (or `come`) means nothing, while a missing one means the default.

`lock` is `loginctl lock-session`; `screen-off` and `wake` use KDE's
`kscreen-doctor` and the screen saver's `SimulateUserActivity`;
`pause-media` pauses the media players that are playing (MPRIS) and
`resume-media` starts only those again. Careful with `screen-off` on
screens behind a dock: in standby they can drop off the DisplayPort bus and
come back under new names, and KDE may then arrange them differently (seen
with an Intel laptop and a dock; KDE's own screen-off does the same). Turning
off "deep sleep" / "auto standby" in the screens' menus usually keeps them
connected. `away light` shows that lighting (`--live`, nothing is stored)
from the moment you leave until you come back or the service stops, then
the stored lighting and the saved software effect return. A software effect
pauses while the screen is locked, so together with `lock` take one of the
keyboard's own effects. Coming back drops what leaving
still had waiting (no screen-off after you sat down again), and the other
way round. Without a config file: leave =
`pause-media`, come = `wake, resume-media`. It reads the distance twice a
second and decides on the median of the last five readings (single ones
jump by a few centimetres), keeps waiting while the keyboard is unplugged
or the computer sleeps, and lets other `z20` commands run in between.
While it runs, `z20 status` says what it sees (`presence` in `--json`: at
the desk or away and since when, nothing in view, the keyboard's sensor
off), which the Plasma widget shows. It looks at the active profile every
10 s: with the keyboard's sensor off (`z20 sensor off`, or the switch on
the settings app's Presence page), the keyboard reports no echo at all, and
the service can't see you either.

The sensor sees the nearest thing in front of it: a chair left near the
distance you set looks like someone leaning back. Push the chair back or
turn it aside when you leave, or set `distance` a little shorter than
where the empty chair stands (`z20 sensor watch` shows both). The keyboard's
own leave action wants even more room: it didn't act with the empty chair
at 46-51 cm and the distance at 45 cm, only from about 70 cm on.

The sensor's beam is narrow: leaning back can take you out of it. It then
gets no echo, and the distance the keyboard reports sinks to a few cm,
which means nothing. z20 tells that apart by the keyboard's verdict on each
measurement (see PROTOCOL.md): `z20 sensor` says "nothing in view" then,
and the service keeps what it decided last, so leaning back doesn't count
as leaving and a few cm while you're away don't count as coming back. Leave
the desk with nothing in the beam either (no chair, no wall within reach),
and the service can't tell that from leaning back: it notices you leaving
once it sees something beyond the distance, such as the pushed-back chair.
Without a `distance` of its own in presence.ini, the service also takes
near or far from that verdict, at once, instead of from the smoothed
distance, which needs a few seconds to follow.

To use E1-E5 as desktop shortcuts, give them keys no keyboard has, like
`z20 key E4 key f14`, and bind those in the desktop's shortcut settings.
F13-F18 are free; avoid F20-F23, which X keyboard maps turn into mic mute
and touchpad on / off / toggle.

### Profiles for programs

A profile for a game or any program: while it runs, the
`z20-apps` user service has the keyboard on its profile, and when it ends,
back on the profile it was on before. If you switched profiles meanwhile
(Fn + 1-9, the widget, `z20 profile`), it leaves yours.

```
z20 apps add Cyberpunk2077.exe 3              while it runs: profile 3
z20 apps add AppId=1091500 3                  a Steam game, by its app ID
z20 apps on                                   start the service (also after login)
z20 apps                                      the rules, and which one applies now
z20 apps running                              what runs now, newest first
journalctl --user -u z20-apps -f              what it does
z20 apps run --dry-run                        try: says what it would do
```

The rules are in `~/.config/z20/apps.ini`, one per line, `PROGRAM = PROFILE`:

```ini
[apps]
Cyberpunk2077.exe = 3
AppId=1091500 = 3
blender = 4
*minecraft* = 5
```

PROGRAM is a process name or a word of a process's command line, with `*`
and `?` as in the shell, in upper or lower case alike. A word is a whole
argument or the last part of a path in one: `Cyberpunk2077.exe` names the
game as Wine and Proton run it (`Z:\...\Cyberpunk2077.exe`), and
`AppId=1091500` the process Steam keeps running as long as its game 1091500
does (the number is in the game's store address; `z20 apps running` lists
it with the game's name). `blend` doesn't name `blender`, `*minecraft*`
names any process with minecraft in an argument. Of the programs that run,
the first rule counts: a game that starts while another one runs takes over
if its rule comes first, and gives back when it ends. `z20 apps add` puts a
rule at the end (or gives the one there a new profile), `z20 apps remove`
takes one out and `z20 apps set` writes them all, in a new order; comments
in the file stay.

The service looks at your processes every 2 s (a few milliseconds each
time) and opens the keyboard only to switch, so other `z20` commands and
the widget go on. It takes the file anew when it changes. While the
keyboard is unplugged it waits, and switches once it is back. Stopped while
a program runs (`z20 apps off`, logging out), it also goes back to the
profile from before. A switch loads the profile's lighting, as Fn + 1-9
does.

### The settings app

`z20-settings` has the settings in a window, a page each: **Lighting** (the
lighting presets on a drawing of the keyboard that runs them, colors of
single keys over the effect, a color picker with the desktop's colors),
**Macros**, **Profiles** (their names), **Programs** (profiles for
programs), **Presence** (the keyboard's presence sensor on or off with what
it sees now and the distance over the last two minutes, what the presence
service does on the computer, and what the keyboard itself does when you
leave and its welcome effect when you come) and **Keyboard** (report rate,
rollover, the keys Game Mode blocks). It is in the application menu as "EVGA
Z20"; `z20-settings macros` opens it on a page, and run again while it is
open, the open one shows that page (as the Plasma widget's pencils do). It
changes the keyboard through `z20`, at once; the presets are kept in
`~/.config/z20/presets.json`, which the widget's popup offers too. On the
first start the lighting the keyboard has stored is the first preset (a
built-in one where it is that, else one named after the profile), and
whichever preset is what the keyboard has stored, however it got there, is
marked as applied, in the app and in the popup (`z20 status --json` has the
stored lighting with all its colors and direction, the software effect
stored, `saved_animation`, and the keys' stored colors, `key_colors`).

It is QML with KDE's Kirigami, run by a small Python launcher; it needs
PyQt6 and Kirigami as the distribution has them (Debian, Ubuntu:
`python3-pyqt6`, `python3-pyqt6.qtqml`, `qml6-module-org-kde-kirigami`,
`qml6-module-org-kde-kcmutils`, `qml6-module-org-kde-plasma-plasma5support`;
a KDE Plasma desktop has all but PyQt6). The QML is in `app/qml`;
`app/qml/lib/Z20Data.qml` talks to `z20` for the app and for the
[Plasma widget](https://github.com/Thokas/plasma-evgaz20), whose install
copies it from here.

## Install

```
git clone https://github.com/Thokas/evga-z20.git && cd evga-z20
./install.sh                     # z20 and z20-settings to ~/.local/bin, then the udev rule
z20 backup                       # keep a copy of how the keyboard is set up now
```

`install.sh` needs no root itself. At the end it shows the commands that
need root once and asks whether to run them with `sudo`: installing the
udev rule, which lets the logged-in user reach the keyboard's configuration
interface. Before that it asks about one optional part: the `uleds` module
(now and at boot) with a rule of its own, so that `z20 backlight` is also
a keyboard light UPower offers (see [Keyboard light](#keyboard-light)).
Without a terminal it only shows the commands. Once chosen, `uleds` stays
chosen on later runs; `./install.sh --uleds` adds it later. By hand:

```
sudo install -m644 udev/70-evga-z20.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger --subsystem-match=hidraw --action=change
# optional, for z20 backlight's LED: the uleds module, now and at boot, and its rule
sudo install -m644 modules-load.d/evga-z20.conf /etc/modules-load.d/ && sudo modprobe uleds
sudo install -m644 udev/70-evga-z20-uleds.rules /etc/udev/rules.d/
sudo udevadm control --reload && sudo udevadm trigger --subsystem-match=misc --action=change
```

Needs Python 3.8 or newer and a desktop session with systemd-logind (the rule
uses `uaccess`). The rule opens only USB interface 1, which carries the
configuration reports; the two interfaces that carry your keystrokes stay
root-only. The optional `uleds` rule opens `/dev/uleds`, for the keyboard
light's LED.

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
Without the rule, `z20` works only as root. With the optional `uleds` rule,
such a program can also add LEDs of its own through `/dev/uleds` (which
can confuse UPower), but not change the ones there are.

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

## Tests

All offline, no keyboard needed:

```
python3 -I -m unittest discover -s tests     # z20 (a stand-in keyboard), and the app as below
node --test tests/js/*.test.mjs              # the app's JavaScript: presets, preview, keyboard
```

`tests/test_install.py` runs `install.sh` and `uninstall.sh` in a home of
their own, against a fake `systemctl`. `tests/test_app.py` runs the
settings app offscreen, a scenario at a time, in a home of its own against
a fake `z20` (`tests/app/`): every page, a second start handing its page
to the open one, the first start putting the keyboard's lighting first,
Apply and a rename, keys' own colors stored and shown live, the color
picker; any warning from its QML fails. It needs PyQt6 and the QML modules
above, else it is skipped. Forgejo runs both on every push
(`.forgejo/workflows/test.yml`), GitHub on every pull request
(`.github/workflows/test.yml`).

## Not done yet

- What the presence sensor's sleep, wake and unlock actions send, and its 4
  gesture slots.
- The brightness set with Fn + Up / Down: it changes nothing `z20` can read
  (the profile, the lighting in RAM, the general settings) and isn't
  reported, so `z20` can't show or set it. `--brightness` sets the
  brightness of the effect's colors instead.

## Uninstall

```
./uninstall.sh                   # z20, z20-settings and the user services (stopped first)
# as root: the udev rules and the uleds module's entry
sudo rm -f /etc/udev/rules.d/70-evga-z20{,-uleds}.rules /etc/modules-load.d/evga-z20.conf
rm -r ~/.config/z20 ~/.local/state/z20   # the settings and the backups too
```

`uninstall.sh` keeps the settings and the backups. Remove the Plasma widget
first, with its own `uninstall.sh`, if you have it.

## Changes

What changed in each release: [CHANGELOG.md](CHANGELOG.md).

## Contributing

Issues and pull requests are welcome on GitHub. GitHub Actions runs the
tests on every pull request.

## Note

Not made or endorsed by EVGA. The protocol was worked out from EVGA's
Unleash RGB 1.0.28 for interoperability; this repository contains none of
EVGA's code or files.

## License

MIT, see [LICENSE](LICENSE). The code and documentation were written by AI
(see the note at the top); the facts about the protocol in PROTOCOL.md are
free for anyone to use.
