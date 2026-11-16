# Notes for Claude

## Tests

- z20: `python3 -I -m unittest discover -s tests`, offline: a stand-in
  `Keyboard`, patched time and paths, temp dirs. Never let a test switch the
  real keyboard's profile or lighting: it is in use. It may or may not be
  plugged in; live checks can fail with "no EVGA Z20 connected".
- The app's JavaScript: `node --test tests/js/*.test.mjs` (`tests/js/load.mjs`
  loads `app/qml/lib` without its QML pragmas).
- The app: `tests/test_app.py` runs `tests/app/drive.py` a scenario at a time
  (in the same discover run; skipped without PyQt6 and Kirigami). New behavior
  of the app gets a scenario there. CI: `.forgejo/workflows/test.yml`.
- `./install.sh` restarts the user's running z20 services (presence,
  backlight, animate, apps), and `./uninstall.sh` stops and removes them:
  run them for real only to ship a change. `tests/test_install.py` runs
  both with a scratch HOME and a fake `systemctl` first on PATH.

## The settings app offscreen (`app/`)

`app/z20-settings` is a small PyQt6 launcher for `app/qml/Main.qml`
(Kirigami). It runs without a display:

```sh
s=$(mktemp -d); mkdir -p "$s/home/.local/bin"
# a fake z20 there: the QML runs "$HOME/.local/bin/z20"
HOME="$s/home" QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  timeout 10 python3 -I app/z20-settings lighting
```

It runs until the timeout (exit 124) and prints its QML errors.

- One app per user and home, through a socket in `$XDG_RUNTIME_DIR`
  named after both: a scratch HOME has its own, so a test never hands its
  page to the user's open app. (Don't move it to a long path: socket paths
  end at about 100 characters, and then there is no single app.) A test
  that starts a second one should end it too, or it keeps the test's
  output pipe open.
- The fake `z20` logs its arguments, so a test can check what would have
  run; where the real one is wanted (`leds`, `presence ...`), it can
  `exec python3 -I /home/.../Projects/evga-z20/z20 "$@"` (the path spelled
  out: `~` is the scratch HOME then), which then changes only files under
  the scratch HOME. The presets are `$HOME/.config/z20/presets.json`.
- Driving it: load `app/z20-settings` as a module
  (`importlib.machinery.SourceFileLoader`), replace `QGuiApplication.exec`
  with one that schedules the steps and then calls the real one, call
  `main()`. The window: `sip.cast(QGuiApplication.topLevelWindows()[0],
  QQuickWindow)`; a page: `QMetaObject.invokeMethod(window, "showPage",
  Q_ARG("QVariant", "macros"))`; anything else:
  `QQmlExpression(QQmlEngine.contextForObject(window), window,
  "pageStack.currentItem.presets.length")`, whose `evaluate()` returns
  `(value, isUndefined)` in PyQt6 (objects as `JSON.stringify(...)`).
  Screenshots: `window.grabWindow().save(...)`, then look at them.
- Run steps one after the other (each schedules the next), never at fixed
  offsets: coarse timers swap steps 100 ms apart a few seconds in.
- Colors are Breeze's with a scratch HOME; for the desktop's own scheme add
  `XDG_CONFIG_HOME=<the real ~/.config>` and `QT_QPA_PLATFORMTHEME=kde`.
  Items with `visible: false` get no `Kirigami.Theme` colors (all black).
- Noise: "Created graphical object was not placed in the graphics scene"
  (Kirigami making a page before it places it), "This plugin does not
  support raise()" (offscreen only).

`app/qml/lib` (`Z20Data.qml`, `presets.js`, `macros.js`) is also the Plasma
widget's (`~/Projects/plasma-evgaz20`, whose `install.sh` copies it in): a
change there reaches the widget at its next install, so check the widget
too (its CLAUDE.md says how).
