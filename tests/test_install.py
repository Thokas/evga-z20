"""install.sh and uninstall.sh, in a home of their own with a fake systemctl: what install.sh puts
where (z20, the settings app with its QML and menu entry, the user services), the root part it asks
for (the udev rule, and the optional uleds LED) against a scratch /etc (Z20_ETC) and a fake sudo, at
a terminal (a pty) and without one, and uninstall.sh taking it all away again while it keeps the
settings and backups. Needs only sh. Nothing reaches the user's own services or /etc: systemctl and
sudo are fakes that log their arguments.

Run: python3 -I -m unittest discover -s tests
"""
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNITS = ("z20-presence.service", "z20-animate.service", "z20-backlight.service", "z20-apps.service")
SYSTEMCTL = """#!/bin/sh
echo "$*" >> "$HOME/systemctl.log"
"""
SUDO = """#!/bin/sh
echo "$*" >> "$HOME/sudo.log"
"""
INSTALLED = [".local/bin/z20", ".local/bin/z20-settings", ".local/share/z20/app/qml/Main.qml",
             ".local/share/z20/app/qml/lib/Z20Data.qml", ".local/share/applications/de.thokas.z20-settings.desktop"
             ] + [f".config/systemd/user/{unit}" for unit in UNITS]


class Install(unittest.TestCase):

    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="z20home")
        self.addCleanup(shutil.rmtree, self.home)
        bin_dir = os.path.join(self.home, "fakebin")
        os.makedirs(bin_dir)
        for name, script in (("systemctl", SYSTEMCTL), ("sudo", SUDO)):
            with open(os.path.join(bin_dir, name), "w") as f:
                f.write(script)
            os.chmod(os.path.join(bin_dir, name), 0o755)
        self.etc = os.path.join(self.home, "etc")
        os.makedirs(self.etc)
        self.env = {"HOME": self.home, "PATH": bin_dir + os.pathsep + "/usr/bin:/bin", "LANG": "C.UTF-8",
                    "Z20_ETC": self.etc}

    def run_script(self, name, *args, answers=None):
        """Runs it without a terminal, or with ANSWERS typed at one (a pty as its stdin)."""
        argv = ["sh", os.path.join(ROOT, name), *args]
        if answers is None:
            done = subprocess.run(argv, env=self.env, cwd=self.home, stdin=subprocess.DEVNULL,
                                  capture_output=True, text=True, timeout=60)
        else:
            master, slave = os.openpty()
            try:
                os.write(master, answers.encode())
                done = subprocess.run(argv, env=self.env, cwd=self.home, stdin=slave,
                                      capture_output=True, text=True, timeout=60)
            finally:
                os.close(slave)
                os.close(master)
        self.assertEqual(done.returncode, 0, done.stderr)
        return done

    def etc_has(self, *names):
        """Puts the repository's NAMES (udev/..., modules-load.d/...) in the scratch /etc, as installed."""
        for name in names:
            if name.startswith("udev/"):
                dest = os.path.join(self.etc, "udev", "rules.d", os.path.basename(name))
            else:
                dest = os.path.join(self.etc, name)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy(os.path.join(ROOT, name), dest)

    def sudo_calls(self):
        return self.calls("sudo.log")

    def systemctl_calls(self):
        return self.calls("systemctl.log")

    def calls(self, name):
        log = os.path.join(self.home, name)
        if not os.path.exists(log):
            return []
        with open(log) as f:
            return f.read().splitlines()

    def path(self, rel):
        return os.path.join(self.home, rel)

    def test_install_puts_everything_in_place(self):
        self.run_script("install.sh")
        for rel in INSTALLED:
            self.assertTrue(os.path.exists(self.path(rel)), rel)
        self.assertTrue(os.access(self.path(".local/bin/z20"), os.X_OK))
        with open(self.path(".local/share/applications/de.thokas.z20-settings.desktop")) as f:
            self.assertIn(f"Exec={self.home}/.local/bin/z20-settings\n", f.read())
        calls = self.systemctl_calls()
        self.assertEqual(calls[0], "--user daemon-reload")
        self.assertTrue(calls[1].startswith("--user try-restart "), calls)

    def test_without_a_terminal_it_shows_the_root_commands_and_runs_none(self):
        done = self.run_script("install.sh")
        self.assertIn(f"!!   sudo install -m644 {ROOT}/udev/70-evga-z20.rules {self.etc}/udev/rules.d/", done.stdout)
        self.assertNotIn("uleds", done.stdout)
        self.assertEqual(self.sudo_calls(), [])

    def test_with_uleds_the_commands_have_it_too(self):
        done = self.run_script("install.sh", "--uleds")
        self.assertIn(f"{ROOT}/modules-load.d/evga-z20.conf {self.etc}/modules-load.d/", done.stdout)
        self.assertIn(f"{ROOT}/udev/70-evga-z20-uleds.rules {self.etc}/udev/rules.d/", done.stdout)
        self.assertIn("!!   sudo modprobe uleds", done.stdout)

    def test_at_a_terminal_the_defaults_are_the_rule_without_uleds(self):
        done = self.run_script("install.sh", answers="\n\n")
        self.assertIn("Optional: should z20 backlight also be a keyboard light", done.stdout)
        self.assertEqual(self.sudo_calls(), [
            f"install -m644 {ROOT}/udev/70-evga-z20.rules {self.etc}/udev/rules.d/",
            "udevadm control --reload",
            "udevadm trigger --subsystem-match=hidraw --action=change"])

    def test_at_a_terminal_yes_to_uleds(self):
        self.run_script("install.sh", answers="y\ny\n")
        self.assertEqual(self.sudo_calls(), [
            f"install -m644 {ROOT}/udev/70-evga-z20.rules {self.etc}/udev/rules.d/",
            f"install -m644 {ROOT}/modules-load.d/evga-z20.conf {self.etc}/modules-load.d/",
            f"install -m644 {ROOT}/udev/70-evga-z20-uleds.rules {self.etc}/udev/rules.d/",
            "udevadm control --reload",
            "modprobe uleds",
            "udevadm trigger --subsystem-match=hidraw --subsystem-match=misc --action=change"])

    def test_at_a_terminal_no_to_sudo_runs_nothing(self):
        done = self.run_script("install.sh", answers="y\nn\n")
        self.assertIn("!!   sudo modprobe uleds", done.stdout)
        self.assertEqual(self.sudo_calls(), [])

    def test_uleds_once_chosen_is_kept_and_not_asked_again(self):
        # As before the split: the module's entry there, the rule an older one.
        self.etc_has("modules-load.d/evga-z20.conf")
        done = self.run_script("install.sh", answers="\n")
        self.assertNotIn("Optional:", done.stdout)
        self.assertIn("modprobe uleds", self.sudo_calls())
        self.assertIn(f"install -m644 {ROOT}/udev/70-evga-z20-uleds.rules {self.etc}/udev/rules.d/",
                      self.sudo_calls())

    def test_all_in_place_nothing_is_asked(self):
        self.etc_has("udev/70-evga-z20.rules")
        done = self.run_script("install.sh", answers="")
        self.assertNotIn("!!", done.stdout)
        self.assertNotIn("Optional:", done.stdout)
        self.assertEqual(self.sudo_calls(), [])

    def test_uninstall_removes_it_and_keeps_settings_and_backups(self):
        self.run_script("install.sh")
        for rel in (".config/z20/presets.json", ".local/state/z20/backups/b.json"):
            os.makedirs(os.path.dirname(self.path(rel)), exist_ok=True)
            open(self.path(rel), "w").close()
        os.remove(os.path.join(self.home, "systemctl.log"))
        done = self.run_script("uninstall.sh")
        for rel in INSTALLED + [".local/share/z20"]:
            self.assertFalse(os.path.exists(self.path(rel)), rel)
        self.assertTrue(os.path.exists(self.path(".config/z20/presets.json")))
        self.assertTrue(os.path.exists(self.path(".local/state/z20/backups/b.json")))
        self.assertEqual(self.systemctl_calls(), ["--user disable --now " + " ".join(UNITS), "--user daemon-reload"])
        self.assertIn("Kept your settings", done.stdout)

    def test_uninstall_without_an_install_does_no_harm(self):
        done = self.run_script("uninstall.sh")
        self.assertIn("Removed z20", done.stdout)


if __name__ == "__main__":
    unittest.main()
