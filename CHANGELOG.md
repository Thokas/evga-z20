# Changelog

All notable changes to evga-z20. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- The settings app's Presence page switches the keyboard's presence sensor
  on and off, sets the distance that counts as present (the keyboard's,
  which the presence service goes by too; where presence.ini has one of
  its own, it says so and can drop it), shows what the sensor sees and the
  distance over the last two minutes (before in the Plasma widget), and
  sets the keyboard's welcome
  effect, its length and its colors. It is in parts: the sensor, what
  z20's presence service does on the computer, and what the keyboard
  itself does. Its changes wait for Save (or Ctrl+S); switching pages or
  closing the window with changes not saved asks first, on the Macros page
  as well.
- `z20 sensor welcome EFFECT [MS] [COLOR ...]`: the welcome effects'
  own colors (explosion, barber pole, light bar wave, thunder; in
  `z20 sensor --json` as `welcome_colors`), which were red from the factory
  and hardly stood out from a red lighting. `z20 sensor default` resets
  them too.
- No welcome effect: `z20 sensor welcome nothing`, "Nothing" on the
  Presence page (effect 0 with no length; Unleash has no such choice).
- `z20 sensor` takes several settings in a row, written at once
  (`z20 sensor off leave dark 30`).
- What Unleash sets for an effect besides its colors: `z20 light ... --zone`
  (the keys it runs on: all, or some of numpad, fkeys, numbers, arrows,
  wasd, bars), `--stop never|press|release`, and for reactive `--mode
  typed|one-key|3x3` and `--fade-out 0-100` (as Unleash's slider); in
  `z20 light --json` and `z20 status --json`, in a lighting preset and on
  the Lighting page ("Keys", "Stops", "Lights", "Fade out").
- The presence sensor's effects as the lighting, as Unleash offers them:
  `z20 light explosion|raining|barber|lightbar|thunder` with their colors,
  direction and brightness (shared with the welcome effect of the same
  name), zone, start and stop; on the Lighting page as effects of a preset,
  drawn after how they may look. `z20 sensor --json` names the barber pole
  and the light bar wave `barber` and `lightbar` now, as `z20 sensor
  welcome` takes them.
- The welcome effects' direction (explosion in or out, the barber pole left
  or right) and brightness: `z20 sensor welcome explosion in 60%`, on the
  Presence page, and in `z20 sensor --json` with their colors as
  `welcome_effects`. Explosion has 7 colors, as in Unleash.
- `z20 light ... --on-key` / `--no-on-key`: whether the keyboard's effect
  starts on the first key press, dark until then (also after plugging in,
  a reload or a welcome effect), or as the profile loads; `on_key` in
  `z20 light --json` and `z20 status --json`. A lighting preset has it too
  (the Lighting page: "Starts: On the first key press") and says it either
  way when applied; the presence service's away light never waits for a
  key.
- The presence service says what it sees (at the desk or away, since
  when, nothing in view, the keyboard's sensor off) in
  `$XDG_RUNTIME_DIR/z20-presence.json`, and `z20 status` passes it on
  (`presence`), for the Plasma widget.

### Fixed

- `z20 light default` also resets fade's and rows' colors.

### Changed

- The presence service looks at the active profile every 10 s (was 60 s,
  and only without a `distance` of its own), and logs when the keyboard's
  sensor goes off or on.

## [0.1.0] - 2026-11-17

The first release. Tested on a Z20 Elite ISO with firmware 1.38; the Z20
Elite, Z20 RGB and Z20 RGB ISO should work the same way (please report
how yours does).

### Added

- `z20`, a single Python file with no dependencies, which talks to the
  keyboard's configuration interface over hidraw. It sends only commands
  from a fixed list (never firmware, reset or factory-reset commands),
  saves what it replaces before each write, and reads every write back
  to check it.
- **Lighting** per profile: off, static, breathing, wave, spiral, pulse,
  stars, reactive and more, with colors, brightness, speed and direction.
  Changes take effect through the keyboard's RAM, without a reload.
- **Live lighting** in RAM only (`z20 light --live`) and colors per key,
  light bar LED and logo (`z20 color`), also over the software effects.
- **Software effects** (`z20 animate`): aurora, fire, rain, ripple,
  scanner and a color gradient, 25 frames a second, as a user service
  that also starts after login.
- **Keyboard light** (`z20 backlight`): a brightness of the Z20's own,
  dimmed and turned off with KDE Plasma's keyboard light (screen dimming,
  screen off, closed lid), set by Plasma's slider. Optionally also an LED
  that UPower offers as a keyboard light (through the kernel's `uleds`).
- **Profiles and Game Mode**: switch profiles 1–9, rename and copy them,
  turn Game Mode on or off and choose the keys it blocks; report rate and
  n-key rollover.
- **Keys** (`z20 key`): see and change what any key does, E1–E5 and the
  Fn layer included (a stored macro once, N times, toggled or held; a key
  combination, media key, click, profile), and back to the factory
  setting one by one or all at once.
- **Macros** (`z20 macro`): list them step by step; create, edit, rename
  and delete them.
- **Presence sensor** (`z20 sensor`, `z20 presence`): its settings per
  profile and the live distance; a user service that locks the screen,
  turns the screens off, pauses media, sets a lighting while you're away
  or runs a command of your own when you leave and come back, each with
  an optional delay.
- **Profiles for programs** (`z20 apps`): while a game or other program
  runs, the keyboard is on its profile, and back on the one from before
  when it ends (Steam and Proton games included).
- **Backup and restore** of all nine profiles and the stored macros
  (`z20 backup`, `z20 restore`), kept readable by you only.
- **Keyboard events** (`z20 events`): profile, Game Mode and other
  changes made with the keyboard's own keys, as they happen.
- **JSON output** (`--json`) for widgets and scripts.
- **Settings app** (`z20-settings`, "EVGA Z20" in the application menu):
  lighting presets on a drawing of the keyboard with colors per key and a
  color picker, macros, profile names, profiles for programs, presence
  and the keyboard's own settings, a page each. QML with KDE's Kirigami;
  its shared part (`app/qml/lib`) is also used by the
  [Plasma widget](https://github.com/Thokas/plasma-evgaz20).
- `install.sh` (no root itself; it shows the udev rule's commands and
  asks whether to run them with `sudo`, the `uleds` LED as an optional
  part) and `uninstall.sh` (keeps your settings and backups).
- [PROTOCOL.md](PROTOCOL.md): the configuration protocol, worked out from
  Unleash RGB 1.0.28 for interoperability.
- Tests that need no keyboard: `z20` against a stand-in keyboard, the
  install scripts, the settings app offscreen and its JavaScript.

[Unreleased]: https://github.com/Thokas/evga-z20/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Thokas/evga-z20/releases/tag/v0.1.0
