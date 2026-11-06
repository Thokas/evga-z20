# EVGA Z20 configuration protocol

What `z20` knows about how the Z20 is configured over USB. It was worked out
from EVGA's Windows software, Unleash RGB 1.0.28 (its .NET assemblies, mainly
`EDispNetLib.dll`), for interoperability, and checked on a Z20 Elite ISO
(`3842:2610`, firmware 1.38). Where something comes only from the software
and wasn't tried on the keyboard, it says so.

## Devices

| USB ID      | Model                  | Bootloader ID |
| ----------- | ---------------------- | ------------- |
| `3842:260a` | Z20 Elite              | `2609`        |
| `3842:260c` | Z20 RGB                | `260b`        |
| `3842:2610` | Z20 Elite ISO ("UK")   | `260f`        |
| `3842:2617` | Z20 RGB ISO ("UK")     | `2616`        |

Unleash drives all four with the same code. The bootloader IDs belong to a
keyboard in firmware-update mode; leave those alone.

The keyboard has three USB interfaces:

- **0**: boot keyboard (6 keys at a time).
- **1**: mouse (report 1, used by mouse-click macros), consumer keys
  (report 2: media keys, volume wheel), system control (report 0x12), a
  status input report 3, and the **configuration feature reports** below.
  Report 3 says when Game Mode changes: `03 03 01` on, `03 03 00` off.
- **2**: n-key rollover keyboard (report 0x10).

Only interface 1 is needed. The hidraw nodes of interfaces 0 and 2 carry every
keystroke, so the udev rule in this repository opens interface 1 only.

## Transactions

Every command is a feature report on interface 1: the host sends it
(SET_FEATURE), waits a few milliseconds, and reads the same report ID back
(GET_FEATURE, same length). The answer repeats the header with a status in
byte 6: `C0` success, `C1` failed, `C2` busy. Reading a report without sending
a request first gives zeros. Unleash waits 5 ms for most report 4 commands,
10 ms for the firmware version, 20 ms after a profile read, 100 ms after
writes and 150 ms around macros.

All reports start with the report ID, then `EA 02`.

| Report | Length (with ID) | Use |
| ------ | ---------------- | --- |
| 4      | 17   | general commands |
| 5      | 521  | firmware update: **don't** |
| 6      | 792  | colors per LED (live) |
| 7      | 136  | lighting effect (live, RAM) |
| 8      | 1806 | one profile: name, key functions, lighting |
| 9      | 1032 | one macro, or the table of used macro slots |
| 10     | 59   | a macro's name |
| 11, 12 | 2056, 59 | recorded light effect for the distance sensor: data, name |
| 15     | 264  | data kept for the software |

## Report 4: general commands

`04 EA 02 <command> <sub 1> <sub 2> <status> <value> ...` (17 bytes). Sub 1 is
`01` to read and `00` to write. The value (byte 7) is what is written, or
what the answer carries.

| Command | Read answer / write value | `z20` |
| ------- | ------------------------- | ----- |
| `01` firmware version | bytes 7, 8: minor, major (`26 01` = 1.38); sub 1 `00` asks the bootloader's | reads |
| `06` active profile | 1-9 | reads, writes |
| `07` key function in RAM | sub 2 = layer (0 normal, 1 Fn), byte 7 = key position, bytes 8-11 = function; write: the same with sub 1 `00` (in Unleash's code, unused there; checked) | reads, writes |
| `08` reload the active profile | write after changing it with report 8 | writes |
| `0B` Game Mode ("E key mode") | 0 off, 1 on | reads, writes |
| `0C` keys blocked in Game Mode (RAM) | bit mask, see below | |
| `0F` 6KRO / NKRO | 0 6KRO, 1 NKRO | reads |
| `11`, `1B` report rate | 0 4000 Hz, 1 2000, 2 1000, 3 8000 | |
| `12` save RAM to the profile | profile number, 0 = active | |
| `22` flash layout | | |
| `30` Fn key off, `33` key position reports (from Unleash's code: write 1 and the keyboard reports the position of pressed keys on interface 1), `34` external flash, `41`-`44` distance sensor | | |
| `02` reset, `03` **erase firmware**, `04` **enter bootloader**, `09` reset profile, `31` **factory reset** | | never |

Game Mode blocks (bits): 1 Alt+Tab, 2 Tab, 4 Ctrl+Esc, 8 Alt+F4, 0x10 left
Shift, 0x20 menu key, 0x40 Windows key. The profile (byte 136) and command
`0C` keep them inverted: a set bit lets the key through (`BF`: only the
Windows key blocked). Unleash writes byte 136 and the report rate (byte 137)
into the active profile, then reloads; `z20` sends `0C` and the rate command
below instead (checked, both read back as written).

The report rate has a command of its own in report 7: `07 EA 02 1B <00 set /
01 read / 02 default> 00 00 <checksum> <rate>`, checksum the negated rate,
rate 0 4000, 1 2000, 2 1000 Hz (3, 8000, isn't offered for the Z20). OpenRGB
sends `07 EA 02 1B 00 00 00 FE 02` as a "sleep timer": that sets 1000 Hz.

6KRO / NKRO: `04 EA 02 0F 00 00 00 <0 or 1>` (checked).

## Report 8: a profile

Request: `08 EA 02 01 <n>` (read profile n, 1-9; 254 is the factory default).
To change one, read it, change bytes, set byte 3 to `00` (write), recompute
the checksum and send the whole report; then send `04 EA 02 08 00` (reload) if
it is the active profile. That is how Unleash assigns keys. The reload
restarts the lighting effect, and an effect set to start on a key press then
stays dark until a key is pressed. So `z20` writes the profile and puts the
changed parts into RAM instead: report 7 blocks for lighting and sensor,
`04 EA 02 07 00 <layer> 00 <key> <function>` for single keys (checked: the
wave kept running, and each part reads back as written). It reloads only
for changes without a RAM part, like a whole restored profile.

| Bytes | Content |
| ----- | ------- |
| 7     | checksum |
| 8-9   | name length, in UTF-16 characters |
| 10-135 | name, UTF-16LE ("DEFAULT 1") |
| 136   | keys blocked in Game Mode |
| 137   | report rate |
| 152-182 | distance sensor settings |
| 264-747 | key functions, normal layer: 121 × 4 bytes by key position |
| 748-1231 | key functions, Fn layer |
| 1288  | lighting effect |
| 1289  | effect's direction or sub mode |
| 1320- | settings of every effect, see below |

### Presence sensor

Bytes 152-182 of a profile; 2-byte values little-endian. From Unleash's
code and the profiles read. Checked: with the distance at 450 mm and
"leave: dark" after 10, the lighting went dark about 12 s after leaving (so
the leave time is in seconds), and the welcome effect played on coming
back; the keyboard sent no report on interface 1 either time. "Leave:
lock" locked KDE about 10 s after leaving, again with nothing on interface
1: the keyboard types Win+L on its keyboard interfaces, which KDE takes as
Meta+L. The sleep, wake and unlock actions haven't been tried.

The leave action fires **once**, then not again until the keyboard is
plugged in or the active profile is written (report 8) and reloaded; a
reload alone doesn't arm it again. It also needs a clear absence: with
the distance at 450 mm, 36 s of readings between 459 and 509 mm didn't
count as gone; every absence that did read 0.7 m or more, or "nothing in
range" (65533). Checked several times: after plugging
in, the first walk-away locked and the second, with nothing sent in
between, didn't; the same after a profile write and reload; after a plain
reload, nothing. So the keyboard's own lock suits a single absence, not a
day at the desk.

The sensor settings are also in RAM, report 7 blocks `03` on, `04`
distance, `05` come time, `06` come action, `07` leave time, `08` leave
action, `09` welcome effect, `0A` welcome length, each the profile's value
padded with zeros (checked: all eight equal). Unleash writes `03`-`08` in
this order and then saves (`04 EA 02 12 00`). Whether the sensor's logic
takes them from there is unclear (the tests ran into the once-only leave
action), so `z20` writes the profile and reloads instead. Unleash's sliders: 10-120
cm, come after 0-10 s, leave after 10-999 s; it offers come: nothing, wake
up, unlock, and leave: nothing, sleep, lock, dark.

| Bytes | Content | Profile 1 here |
| ----- | ------- | -------------- |
| 152 | on (1) / off (0) | on |
| 153-154 | distance that counts as present, mm (Unleash shows cm) | 1200 |
| 155-156 | time before "approaching" acts, ms | 0 |
| 157-158 | when approaching: 0 turn on, 1 wake up, 2 unlock, `FFFF` nothing | nothing |
| 159-160 | time before "leaving" acts, s | 10 |
| 161-162 | when leaving: 0 turn off, 1 sleep, 2 lock, 3 dark, `FFFF` nothing | dark |
| 163-178 | 4 gestures, each a key function | disabled |
| 179-180 | welcome effect when approaching (effect number, sub mode) | 22, 0 |
| 181-182 | welcome effect's length, ms | 5000 |

The current distance: `04 EA 02 41 01`, answer bytes 7-8, mm. Checked over
a few minutes: 240-430 at the desk, 0.5-1.3 m with the chair pushed back,
around 0.5 m with the chair in place, under 100 with a hand over the
sensor. Unleash polls it for its live display.

The status report on interface 1 (report 3) tells what changed on the
keyboard itself: `03 <what> <value>`, what = 0 profile, 1 lighting effect,
2 6KRO / NKRO, 3 Game Mode (`03 03 01` on), 4 reset to default, 6 key
position. Checked: Fn + 2 and Fn + 1 send `03 00 02` and `03 00 01` (the
profile number as is), the Game Mode key `03 03 01` and `03 03 00`. Media
keys and the volume wheel come as report 2 (consumer usage, then `00 00`).

Not found: the brightness set with Fn + Up / Down. Two steps down changed no
byte of the profile, of the lighting blocks in RAM or of the general
settings readable with report 4, and sent no status report.

### Key functions

4 bytes: function, then three parameters.

| Function | Parameters |
| -------- | ---------- |
| `00` key | modifier bits (1 LCtrl, 2 LShift, 4 LAlt, 8 LGUI, 0x10-0x80 the right ones), HID key usage, a second usage |
| `02` media key | HID consumer usage, little-endian |
| `03` macro | macro number, run mode, repeat count |
| `04` Fn, `05` Game Mode key | |
| `06` wheel | 0 up, 1 down |
| `07`, `08`, `09` | left, right, middle click |
| `11`-`19` | profile 1-9; `1E`, `1F` next / previous profile |
| `FF` | disabled (`FF 00 00 00`, as Unleash writes it and the factory profile has it) |

Macro run modes: `00` loop, `01` once, `02` multi-stage, `03` repeat, each
started on key release; `08`-`0B` the same started on key press; `04`
two-phase; `0C` while held. Unleash offers three of them for a key: `0B`
with a count (repeat N times), `08` (loop until the key is pressed again)
and `0C` (while held). Checked on the keyboard:

- `08`: a press starts the loop, the next press stops it.
- `09`: runs once.
- `0B`: runs count + 1 times. Unleash writes its "repeat" number unchanged,
  so its default 1 means two runs.
- `0C`: runs again and again while the key is held, and stops as soon as it
  is let go, also in the middle of the macro, releasing the keys it held.

The Fn layer (bytes 748-1231) is what Fn + the key does. Key functions take
HID usages up to `FF`, so F13-F24 (`68`-`73`) work: Fn + E4 set to `00 00 69 00`
sends F14.

The factory profile (254) has E1-E5 disabled; for the other keys both
layers hold the key itself (the Fn layer of W is W). Checked: CapsLock set to
`00 01 00 00` sends left Ctrl, and Fn + Q set to `00 00 6B 00` sends F16.

What Unleash leaves alone: it offers no Fn layer for 1-0, F12, both Alt keys
and the arrows (Fn + those are the keyboard's own: profiles, recording
macros, brightness and effect), and its "reset keys" copies both key tables
from the factory profile but keeps the Windows key (104) and Fn (108) as
they were, and deletes all macros. `z20 key all default` does the same
without deleting macros, and `z20` never changes Fn.

Key positions: 0 Game Mode key, 1 Esc, 2-13 F1-F12, 14 Print, 15 Scroll Lock,
16 Pause, 18-20 media previous / play / next, **21 E1**, 22 `` ` ``, 23-32 1-0,
33 -, 34 =, 35 Backspace, 36 Insert, 37 Home, 38 Page Up, 39 Num Lock, 40-42
keypad / * -, **43 E2**, 44 Tab, 45-54 Q-P, 55 [, 56 ], 57 \, 58 Delete, 59
End, 60 Page Down, 61-63 keypad 7-9, 64 keypad +, **65 E3**, 66 Caps Lock,
67-75 A-L, 76 ;, 77 ', 78 Enter, 79-81 keypad 4-6, **82 E4**, 83 left Shift,
84-90 Z-M, 91 `,`, 92 ., 93 /, 94 right Shift, 96 Up, 98-100 keypad 1-3, 101
keypad Enter, **102 E5**, 103 left Ctrl, 104 Windows, 105 left Alt, 106 Space,
107 right Alt, 108 Fn, 109 Menu, 110 right Ctrl, 111-113 Left / Down / Right,
114 keypad 0, 115 keypad ., 116-117 volume wheel up / down, 118 mute, 119 ISO
`#`, 120 ISO `\`. LEDs only: 160-168 left light bar, 176-184 right light bar,
192-195 logo.

### Lighting

Effect numbers (byte 1288): 0 off, 1 static, 2 breathing, 3 pulse, 4 spiral
rainbow, 5 rainbow wave, 6 star shining, 7 trigger (reactive), 16 fade in/out,
17 by row; 18-23 are effects for the distance sensor (explosion, raining,
hair salon, light bar wave, thunder, recorded).

Each effect keeps its own settings, so switching effects keeps what was set
before. Every block starts with zone (0x80 all; or bits 1 numpad, 2 F keys,
4 number keys, 8 arrows, 0x10 WASD, 0x20 light bars), start mode (0 with the
profile, 1 on a key press) and stop mode (0 never, 1 on press, 2 on release).
Colors are 4 bytes: brightness, red, green, blue.

| Bytes | Effect | Fields after zone, start, stop |
| ----- | ------ | ------------------------------ |
| 1320-1339 | static | 13 reserved, color at 1336 |
| 1340-1367 | breathing | random, 12 reserved, cycle ms (1356, 2 bytes LE), 2 × (hold %, color) |
| 1368-1424 | pulse | random, 12 reserved, cycle ms, colors per cycle, on hold %, off hold %, background color, 8 colors |
| 1425-1475 | spiral | direction (0 clockwise, 1 counter), 12 reserved, cycle ms, colors per cycle, 8 colors |
| 1476-1526 | wave | random, direction (0 up, 1 down, 2 right, 3 left), 11 reserved, cycle ms, colors per cycle, 8 colors |
| 1527-1577 | trigger | random, sub mode (0 typed key, 1 one key, 2 3×3 around it), 11 reserved, color shift ms, colors per cycle, 8 colors |
| 1578-1596 | stars | 13 reserved, cycle ms, brightness |
| 1597-1616 | fade | random, 1 for the software, 11 reserved, color |
| 1617-1661 | by row | random, 1 for the software, 11 reserved, colors per cycle, 7 colors |

When an effect is written, Unleash puts its direction (spiral, wave) or sub
mode (trigger) into byte 1289 as well, and 0 for the others.

Not found yet: where the brightness set with Fn + Up / Down is kept.

### Lighting in RAM (report 7)

The active profile's lighting is also in RAM, block by block:
`07 EA 02 <block> <00 write / 01 read> 00 <status> <checksum> <128 bytes>`.
Block `0C` holds the effect number and its direction or sub mode; `0D`
static, `0E` breathing, `0F` pulse, `10` spiral, `11` wave, `12` trigger,
`13` stars, `14` fade, `15` by row hold each effect's settings in the same
layout as in the profile, padded with zeros (checked: all nine read back
equal to the stored profile). The checksum is the negated sum of the 128
bytes. A read is answered like other commands (status `C0`); Unleash sends
writes without reading an answer, and a read afterwards shows the new
values. Writing `0C` and an effect block changes the lighting at once;
`04 EA 02 08` (reload) brings back what is stored, and `04 EA 02 12`
(save) would store the RAM instead. When a profile is loaded, the keyboard
fills block `0C`'s second byte with the effect's direction (`02` for a wave
to the right), where the stored profile may have `FF`.

Blocks `03`-`0A` hold the presence sensor's settings (on, distance,
approach time and action, leave time and action, welcome effect) and `0B`
key functions; Unleash writes those, then saves. `z20` writes `03`-`0A` too,
after writing a profile, and leaves `0B` alone (single keys go through
report 4 command `07`).

Report 7 with `00` or `01` in byte 3 is something else: Unleash's "sync"
previews, which run an effect without touching the profile until
`07 EA 02 00` ends them. `z20` doesn't use them.

### Colors per LED (report 6)

`06 EA 02 01 00 00 00 <checksum>`, then 196 × brightness, red, green, blue
by LED position (the key positions above, the light bars 160-168 and
176-184, the logo 192-195), shows those colors over the running lighting;
`06 EA 02 00` ends that. The checksum is the negated sum of the 784 color
bytes. Sent without reading an answer, as Unleash does for its software
effects, which send a new frame for each step. Checked: one frame stays
until it is ended.

## Reports 9 and 10: macros

The keyboard keeps up to 100 macros.

- Used slots: send `09 EA 02 01 00 00 C1`, wait 150 ms, read: bytes 8-107
  are 1 for each used slot 1-100.
- One macro: `09 EA 02 01 <n> 00 C1`, wait 150 ms, read 1032 bytes.
- Only its name: `0A EA 02 01 <n> 00 C1`, wait 10 ms, read 59 bytes.

| Bytes | Content |
| ----- | ------- |
| 7     | checksum |
| 8     | name length |
| 9-58  | name, UTF-8 |
| 59-61 | run mode, repeat count, time unit: not used by Unleash 1.0.28, which sets the run mode in the key function |
| 62-63 | data length |
| 64-1030 | data |
| 1031  | 1 in use, `FF` deleted |

Data, one step after another:

| Bytes | Step |
| ----- | ---- |
| `01 lo hi` | wait (value + 1) / 2 ms |
| HID key usage (`04`-`65`), modifiers `70`-`77` (LCtrl, LShift, LAlt, LGUI, RCtrl, RShift, RAlt, RGUI) | key down; with 0x80 added: key up |
| `7A` / `7B` / `7C` | left / right / middle button down; `FA` / `FB` / `FC` up |
| `78` / `F8` | wheel down / up |
| `03 lo hi` | media key down (consumer usage); `03 00 00` up |
| `80 x x y y` | move the mouse to x, y |

Unleash puts a wait before every step: where it recorded none, `01 04 00`
(2.5 ms). The keyboard needs that: it reports its keys at a fixed rate, and
steps without a wait between them merge. Checked: "LShift down, H down, H up,
LShift up, I down, I up" without waits typed Shift + H with the Shift let go
first and no "i" at all; with 2.5 ms before each step it typed "Hi".

Writing (checked): the same report with byte 3 `00`, byte 6 `C1`, the
checksum and status 1; bytes 59-61 and everything after the data stay 0, as
in the macros Unleash stores. Reading the macro back gives exactly what was
written. Deleting: status `FF`, both lengths 0; the slot table then shows the
slot free (`FF`). A macro is put on a key with a key function `03`. Unleash
tells macros apart by name, so names should be unique.

## Checksums

Profiles (report 8) and macros (report 9) carry in byte 7 the negated sum
of all bytes after it, so all bytes from 7 on add up to 0 (mod 256).
