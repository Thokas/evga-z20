"""Drives z20-settings offscreen through one scenario, in this process, and prints what it saw as one
line, RESULT {json}, with the warnings its own QML gave. For tests/test_app.py, which runs it in a home
of its own with a fake z20 (fake_z20): python3 -I drive.py SCENARIO [PAGE]."""
import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys

from PyQt6 import sip
from PyQt6.QtCore import QMetaObject, QTimer, Q_ARG, qInstallMessageHandler
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlEngine, QQmlExpression
from PyQt6.QtQuick import QQuickWindow

APP = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "app", "z20-settings"))
QML = os.path.join(os.path.dirname(APP), "qml")
# Not the app's: Kirigami making a page before placing it, offscreen windows that can't be raised.
NOISE = ("not placed in the graphics scene", "does not support raise")
result = {"warnings": []}
started = []  # other runs of the app


def heard(mode, context, message):
    if mode.name in ("QtWarningMsg", "QtCriticalMsg", "QtFatalMsg") and QML in (context.file or "") + message \
            and not any(n in message for n in NOISE):
        result["warnings"].append(f"{(context.file or '').split('/')[-1]}:{context.line}: {message}")


def window():
    return sip.cast(QGuiApplication.topLevelWindows()[0], QQuickWindow)


def evaluate(obj, code):
    e = QQmlExpression(QQmlEngine.contextForObject(obj), obj, code)
    value = e.evaluate()
    if e.hasError():
        raise RuntimeError(f"{code}: {e.error().toString()}")
    return value[0] if isinstance(value, tuple) else value


def win(code):
    return evaluate(window(), code)


def page(code):
    """In the page shown, where its ids are (z20, keyboard, picker, showLive)."""
    return evaluate(win("pageStack.currentItem"), code)


def home(*parts):
    return os.path.join(os.environ["HOME"], *parts)


def log():
    with open(home("z20.log")) as f:
        return f.read().splitlines()


def presets():
    try:
        with open(home(".config", "z20", "presets.json")) as f:
            return json.load(f)
    except OSError:
        return None


def state():
    try:
        with open(home(".local", "state", "z20", "preset")) as f:
            return f.read()
    except OSError:
        return None


def show(name):
    QMetaObject.invokeMethod(window(), "showPage", Q_ARG("QVariant", name))


def note(**values):
    result.update(values)


def visit_pages():
    note(pages=[])
    steps = []
    for name in ("lighting", "macros", "profiles", "programs", "presence", "keyboard"):
        steps += [(10, lambda n=name: show(n)),
                  (700, lambda: result["pages"].append([win("current"), win("pageStack.currentItem.title")]))]
    return steps + [
        (10, lambda: started.append(subprocess.Popen([sys.executable, "-I", APP, "macros"]))),
        (2000, lambda: note(second_exit=started[0].poll(), after_second=win("current"))),
    ]


def read():
    note(presets=[p["name"] for p in presets() or []], shown=page("preset ? preset.name : ''"),
         applied=page("appliedIndex"), current=page("current"))


SCENARIOS = {
    "pages": lambda: [(1500, lambda: note(first=win("current")))] + visit_pages(),
    "seed": lambda: [(3500, read)],
    "apply": lambda: [
        (3500, lambda: page("current = presets.findIndex(p => p.name === 'Ocean')")),
        (300, lambda: page("z20.applyPreset(preset, false)")),
        (1500, lambda: note(log=log(), state=state())),
        (10, lambda: page("change('name', 'Ocean 2')")),
        (1500, lambda: note(state_renamed=state(), names=[p["name"] for p in presets() or []])),
    ],
    "on-key": lambda: [
        (3500, lambda: page("current = presets.findIndex(p => p.name === 'Ocean')")),
        (300, lambda: page("onKey.toggle(); onKey.toggled()")),
        (300, lambda: note(shown=page("onKey.visible"), checked=page("onKey.checked"))),
        (10, lambda: page("z20.applyPreset(preset, false)")),
        (1500, lambda: note(log=log(), presets=presets())),
    ],
    # Reactive with what Unleash sets for it too: some keys, stopped when let go, 3x3 around, a longer glow.
    "unleash": lambda: [
        (3500, lambda: page("current = presets.findIndex(p => p.name === 'Typing')")),
        (300, lambda: page("setZone('wasd', true); setZone('arrows', true)")),
        (100, lambda: page("stopBox.activated(2); modeBox.activated(2); fadeOut.value = 20; fadeOut.moved()")),
        (300, lambda: note(shown=[page("stopBox.visible"), page("modeBox.visible"), page("allKeys.visible")],
                           all_keys=page("allKeys.checked"))),
        (10, lambda: page("z20.applyPreset(preset, false)")),
        (1500, lambda: note(log=log(), presets=presets())),
    ],
    "keys": lambda: [
        (3500, lambda: page("current = presets.findIndex(p => p.name === 'Rainbow'); keyboard.select(['W', 'A'], true)")),
        (300, lambda: page("setKeys(keyboard.selected, 'ff0000'); showLive.checked = true; liveLater.restart()")),
        (1500, lambda: note(selected=page("keyboard.selected.length"),
                            keys=next((p.get("keys") for p in presets() or [] if p["name"] == "Rainbow"), None),
                            log=log())),
    ],
    # The keyboard's own settings on the presence page: as read, then another welcome effect, its length and
    # colors, sent on Save.
    "welcome": lambda: [
        (3500, lambda: note(shown=page("welcomeBox.currentText"), length=page("welcomeLengthBox.value"),
                            colors=json.loads(page("JSON.stringify(welcomeColors)")))),
        (10, lambda: page("welcomeBox.activated(welcomeChoices.findIndex(c => c.id === 'thunder'))")),
        (10, lambda: page("welcomeLengthBox.value = 3000; welcomeLengthBox.valueModified()")),
        (10, lambda: page("picker.slot = 0; picker.picked('0000ff')")),
        (10, lambda: page("welcomeLevel.value = 60; welcomeLevel.moved()")),
        (1000, lambda: note(unsaved=log(), chosen=page("welcomeBox.currentText"), dirty=page("dirty"))),
        (10, lambda: page("saveButton.clicked()")),
        (1500, lambda: note(log=log(), dirty_after=page("dirty"))),
    ],
    # The barber pole's direction as stored; Explosion, turned inward.
    "welcome-direction": lambda: [
        (3500, lambda: note(ways=json.loads(page("JSON.stringify(welcomeWay.model)")), way=page("welcomeWay.currentText"))),
        (10, lambda: page("welcomeBox.activated(welcomeChoices.findIndex(c => c.id === 'explosion'))")),
        (10, lambda: page("welcomeWay.activated(1)")),
        (300, lambda: note(explosion_colors=page("welcomeColors.length"))),
        (10, lambda: page("save()")),
        (1500, lambda: note(log=log())),
    ],
    # The keyboard's sensor off and its leave action changed: one write on Save.
    "sensor": lambda: [
        (3500, lambda: note(on=page("sensorSwitch.checked"), now=page("sensorSwitch.text"))),
        (10, lambda: page("sensorSwitch.toggle(); sensorSwitch.toggled()")),
        (10, lambda: page("change('keyboardLeave', 'lock')")),
        (1000, lambda: note(unsaved=log())),
        (10, lambda: page("save()")),
        (1500, lambda: note(log=log())),
    ],
    # The keyboard's distance, and the service's own (presence.ini) given up for it.
    "distance": lambda: [
        (3500, lambda: note(shown=page("distanceBox.value"), own=page("ownDistance.visible"), band=page("withinMm"))),
        (10, lambda: page("distanceBox.value = 45; distanceBox.valueModified()")),
        (10, lambda: page("ownDistance.actions[0].trigger()")),
        (300, lambda: note(band_after=page("withinMm"))),
        (10, lambda: page("save()")),
        (1500, lambda: note(log=log())),
    ],
    # A change not saved: another page asks first; Discard drops it.
    "discard": lambda: [
        (3500, lambda: page("change('leaveAfter', 45)")),
        (10, lambda: show("keyboard")),
        (700, lambda: note(asked=win("discardDialog.opened"), still=win("current"))),
        (10, lambda: win("discardDialog.customFooterActions[0].trigger()")),
        (1500, lambda: note(after=win("current"), log=log())),
    ],
    "picker": lambda: [
        (3500, lambda: page("keyboard.select(['Q'], true); picker.slot = -1; picker.openAt(keysColor, '')")),
        (700, lambda: note(opened=page("picker.opened"),
                           desktop=json.loads(page("JSON.stringify(picker.desktopColors.map(c => [c.name, c.color]))")))),
        (10, lambda: page("picker.pick(picker.desktopColors[0].color)")),
        (700, lambda: note(q=page("preset.keys ? preset.keys.Q || '' : ''"), closed=not page("picker.opened"))),
    ],
}


def run(steps, i=0):
    if i < len(steps):
        delay, step = steps[i]

        def go():
            try:
                step()
            except Exception as e:  # noqa: BLE001 - reported, and the run ends
                note(error=f"{type(e).__name__}: {e}")
                finish()
                return
            run(steps, i + 1)
        QTimer.singleShot(delay, go)
    else:
        finish()


def finish():
    for other in started:
        if other.poll() is None:
            other.kill()
    print("RESULT " + json.dumps(result), flush=True)
    QGuiApplication.quit()


def main():
    scenario, start = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "lighting")
    loader = importlib.machinery.SourceFileLoader("z20settings", APP)
    app = importlib.util.module_from_spec(importlib.util.spec_from_loader("z20settings", loader))
    loader.exec_module(app)
    qInstallMessageHandler(heard)
    exec_ = QGuiApplication.exec

    def exec_with_steps():
        run(SCENARIOS[scenario]())
        return exec_()
    QGuiApplication.exec = staticmethod(exec_with_steps)
    sys.argv = [APP, start]
    return app.main()


if __name__ == "__main__":
    sys.exit(main())
