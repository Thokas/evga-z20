"""The settings app (app/), offscreen: each test runs it through a scenario (tests/app/drive.py) in a home
and runtime dir of its own, against a fake z20 (tests/app/fake_z20), and checks what it did and that its
QML gave no warnings. Needs PyQt6 (with QtQml, QtQuick) and KDE's Kirigami, kcmutils and plasma5support
QML modules (see .forgejo/workflows/test.yml); without them the tests are skipped, and with
Z20_APP_TESTS=required (CI) that is an error instead.

Run: python3 -I -m unittest discover -s tests -p test_app.py -v
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def missing():
    """What the app needs that isn't there, else ""."""
    try:
        from PyQt6.QtCore import QLibraryInfo
        import PyQt6.QtQml  # noqa: F401
        import PyQt6.QtQuick  # noqa: F401
    except ImportError as e:
        return str(e)
    qml = QLibraryInfo.path(QLibraryInfo.LibraryPath.QmlImportsPath)
    for module in ("org/kde/kirigami", "org/kde/kcmutils", "org/kde/plasma/plasma5support", "org/kde/desktop",
                   "QtQuick/Dialogs"):
        if not os.path.exists(os.path.join(qml, module, "qmldir")):
            return f"the QML module {module.replace('/', '.')}"
    return ""


MISSING = missing()
if MISSING and os.environ.get("Z20_APP_TESTS") == "required":
    raise RuntimeError(f"the app's tests need {MISSING}")

# A status as z20 status --json gives it (the parts the app reads), with the lighting stored.
STATUS = {"model": "Z20 Elite ISO", "firmware": "1.38", "profile": 1, "profile_name": "DEFAULT 1",
          "game_mode": False, "game_mode_blocks": [], "nkro": True, "report_rate": 1000, "animation": None,
          "saved_animation": None, "key_colors": {}, "backlight": None, "apps": None, "keys": {},
          "changed_keys": {}, "macros": {}}
OWN_WAVE = {"effect": "wave", "colors": ["#ff0000", "#d80c36", "#000000", "#ff0000", "#d82537", "#000000",
                                         "#d8122c", "#ffffff"], "direction": "right", "cycle_ms": 3000, "brightness": 100}
RAINBOW = {"effect": "wave", "colors": ["#ff0000", "#ff8000", "#ffff00", "#00ff00", "#00ffff", "#0000ff",
                                        "#ff00ff", "#ff0000"], "direction": "right", "cycle_ms": 3000, "brightness": 100}

# z20 sensor --json as the keyboard answers it (its welcome effect named as z20 reads it).
SENSOR = {"profile": 1, "on": True, "distance_cm": 50.0, "come": "nothing", "come_after_s": 1.0, "leave": "dark",
          "leave_after_s": 10, "welcome": "barber pole", "welcome_ms": 5000, "distance_mm": 503,
          "seen": ["near"] * 8, "in_view": True}


@unittest.skipIf(MISSING, f"the app's tests need {MISSING}")
class App(unittest.TestCase):

    def drive(self, scenario, lighting=OWN_WAVE, page="lighting", sensor=None):
        home, runtime = tempfile.mkdtemp(prefix="z20home"), tempfile.mkdtemp(prefix="z20rt")
        self.addCleanup(shutil.rmtree, home)
        self.addCleanup(shutil.rmtree, runtime)
        os.makedirs(os.path.join(home, ".local", "bin"))
        shutil.copy(os.path.join(HERE, "app", "fake_z20"), os.path.join(home, ".local", "bin", "z20"))
        with open(os.path.join(home, "status.json"), "w") as f:
            json.dump({**STATUS, "lighting": lighting}, f)
        if sensor:
            with open(os.path.join(home, "sensor.json"), "w") as f:
                json.dump(sensor, f)
        # Nothing of the session: no display, no session bus (D-Bus would start the desktop's services for
        # this home), no XDG dirs.
        env = {k: v for k, v in os.environ.items() if not k.startswith(("QT_", "XDG_", "DBUS_"))
               and k not in ("DISPLAY", "WAYLAND_DISPLAY")}
        env.update(HOME=home, XDG_RUNTIME_DIR=runtime, XDG_CONFIG_HOME=os.path.join(home, ".config"),
                   QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software", Z20_REPO=ROOT)
        done = subprocess.run([sys.executable, "-I", os.path.join(HERE, "app", "drive.py"), scenario, page], env=env,
                              capture_output=True, text=True, timeout=120)
        lines = [line for line in done.stdout.splitlines() if line.startswith("RESULT ")]
        self.assertTrue(lines, f"no result: {done.stdout}\n{done.stderr}")
        result = json.loads(lines[-1][len("RESULT "):])
        self.assertNotIn("error", result, result.get("error"))
        self.assertEqual(result["warnings"], [], "the app's QML warned")
        return result, home

    def test_every_page_and_a_second_start(self):
        r, _ = self.drive("pages")
        self.assertEqual(r["first"], "lighting")
        self.assertEqual(r["pages"], [["lighting", "Lighting"], ["macros", "Macros"], ["profiles", "Profiles"],
                                      ["programs", "Programs"], ["presence", "Presence"], ["keyboard", "Keyboard"]])
        # run again while open, it hands the page over and ends; the open one shows it
        self.assertEqual((r["second_exit"], r["after_second"]), (0, "macros"))

    def test_a_first_start_puts_the_keyboards_own_lighting_first(self):
        r, home = self.drive("seed", OWN_WAVE)
        self.assertEqual(r["presets"][:3], ["Profile 1", "Rainbow", "Ocean"])
        self.assertEqual((r["shown"], r["current"], r["applied"]), ("Profile 1", 0, 0))

    def test_a_first_start_with_a_built_in_lighting_puts_that_first(self):
        r, _ = self.drive("seed", RAINBOW)
        self.assertEqual(r["presets"][0], "Rainbow")
        self.assertNotIn("Profile 1", r["presets"])
        self.assertEqual((r["shown"], r["applied"]), ("Rainbow", 0))

    def test_apply_stores_it_and_a_rename_keeps_it_the_one_applied(self):
        r, _ = self.drive("apply")
        sent = [line for line in r["log"] if line.split()[0] in ("animate", "light", "color")]
        self.assertEqual(sent[-3:], ["animate off", "light wave 0010ff 0060ff 00c0ff 00ffd0 --brightness 100 "
                                     "--cycle 6000 --direction left", "color all none"])
        self.assertEqual(r["state"], "Ocean")
        self.assertEqual(r["state_renamed"], "Ocean 2")
        self.assertIn("Ocean 2", r["names"])

    def test_keys_get_their_color_stored_and_shown_live(self):
        r, _ = self.drive("keys")
        self.assertEqual(r["selected"], 2)
        self.assertEqual(r["keys"], {"W": "ff0000", "A": "ff0000"})
        self.assertIn("color all none W,A ff0000 --live", r["log"])

    def test_the_keyboards_welcome_effect_is_shown_and_set(self):
        r, _ = self.drive("welcome", page="presence", sensor=SENSOR)
        self.assertEqual((r["shown"], r["length"]), ("Barber pole", 5000))  # as z20 sensor --json names it
        self.assertEqual(r["chosen"], "Barber pole")
        self.assertIn("sensor welcome barber 5000", r["log"])
        self.assertIn("sensor welcome barber 3000", r["log"])  # the length, once it stood still

    def test_the_keyboards_sensor_can_be_switched_off(self):
        r, _ = self.drive("sensor", page="presence", sensor=SENSOR)
        self.assertEqual((r["on"], r["now"]), (True, "On"))
        self.assertIn("sensor off", r["log"])

    def test_the_picker_offers_the_desktops_colors(self):
        r, _ = self.drive("picker")
        self.assertTrue(r["opened"])
        names = [name for name, _ in r["desktop"]]
        self.assertEqual(names[0], "Accent")
        self.assertGreaterEqual(len(names), 3)
        self.assertEqual(r["q"], r["desktop"][0][1])  # picked for the key selected
        self.assertTrue(r["closed"])


if __name__ == "__main__":
    unittest.main()
