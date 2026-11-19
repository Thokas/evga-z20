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
    "keys": lambda: [
        (3500, lambda: page("current = presets.findIndex(p => p.name === 'Rainbow'); keyboard.select(['W', 'A'], true)")),
        (300, lambda: page("setKeys(keyboard.selected, 'ff0000'); showLive.checked = true; liveLater.restart()")),
        (1500, lambda: note(selected=page("keyboard.selected.length"),
                            keys=next((p.get("keys") for p in presets() or [] if p["name"] == "Rainbow"), None),
                            log=log())),
    ],
    # The keyboard's own settings on the presence page: as read, then a welcome effect and its length set.
    "welcome": lambda: [
        (3500, lambda: note(shown=page("welcomeBox.currentText"), length=page("welcomeLengthBox.value"))),
        (10, lambda: page("welcomeBox.activated(welcomeChoices.findIndex(c => c.id === 'barber'))")),
        (10, lambda: page("welcomeLengthBox.value = 3000; welcomeLengthBox.valueModified()")),
        (2000, lambda: note(log=log(), chosen=page("welcomeBox.currentText"))),
    ],
    # The keyboard's sensor switched off on the presence page.
    "sensor": lambda: [
        (3500, lambda: note(on=page("sensorSwitch.checked"), now=page("sensorSwitch.text"))),
        (10, lambda: page("sensorSwitch.toggle(); sensorSwitch.toggled()")),
        (1500, lambda: note(log=log())),
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
