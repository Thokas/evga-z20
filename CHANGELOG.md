# Changelog

All notable changes to evga-z20. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project
uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
