"""Offline tests of z20: what it agrees to send, and how it reads and changes reports.

Run: python3 -I -m unittest discover -s tests
"""
import importlib.machinery
import importlib.util
import os
import sys
import unittest

sys.dont_write_bytecode = True
_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "z20")
_loader = importlib.machinery.SourceFileLoader("z20", _path)
z20 = importlib.util.module_from_spec(importlib.util.spec_from_loader("z20", _loader))
_loader.exec_module(z20)


def report(*data, size=None):
    return bytearray(data).ljust(size or z20.SIZES[data[0]], b"\0")


def profile(n=5):
    """A profile report as the keyboard answers a read, with a byte pattern to spot changes."""
    p = report(8, 0xEA, 0x02, z20.READ, n, 0, z20.SUCCESS)
    for i in range(8, len(p)):
        p[i] = i * 7 % 251
    p[7] = z20.checksum(p)
    return p


def changed(a, b):
    return {i for i in range(len(a)) if a[i] != b[i]}


class Requests(unittest.TestCase):
    def test_never_sends_reset_erase_bootloader_or_factory_reset(self):
        # 02 reset, 03 erase firmware, 04 bootloader, 09 reset profile, 31 factory reset, 12 save
        for command in (0x02, 0x03, 0x04, 0x09, 0x31, 0x12):
            for sub in (z20.READ, z20.WRITE):
                with self.assertRaises(z20.Z20Error, msg=hex(command)):
                    z20.check_request(report(4, 0xEA, 0x02, command, sub))

    def test_never_sends_other_reports(self):
        # 5 is the firmware update; 6 and 7 (live lighting) are allowed in part, see LiveLighting
        for rid, size in ((5, 521), (11, 2056), (12, 59), (15, 264)):
            with self.assertRaises(z20.Z20Error):
                z20.check_request(report(rid, 0xEA, 0x02, z20.READ, size=size))

    def test_general_reads_and_writes(self):
        for command in (0x01, 0x06, 0x07, 0x0B, 0x0F):
            z20.check_request(report(4, 0xEA, 0x02, command, z20.READ))
        for command in (0x06, 0x08, 0x0B, 0x0C):
            z20.check_request(report(4, 0xEA, 0x02, command, z20.WRITE))
        z20.check_request(report(4, 0xEA, 0x02, 0x07, z20.WRITE, 1, 0, 45, 0, 0, 0x6B, 0))  # Fn+Q in RAM
        for layer, pos in ((2, 45), (0, 108), (0, 121), (0, 17)):  # no layer 2, not Fn, no such keys
            with self.assertRaises(z20.Z20Error):
                z20.check_request(report(4, 0xEA, 0x02, 0x07, z20.WRITE, layer, 0, pos))
        with self.assertRaises(z20.Z20Error):
            z20.check_request(report(4, 0xEA, 0x02, 0x41, z20.WRITE))  # the sensor's distance: read only
        with self.assertRaises(z20.Z20Error):
            z20.check_request(report(4, 0x00, 0x02, 0x01, z20.READ))  # wrong header

    def test_profile_writes_need_a_number_1_to_9_and_the_checksum(self):
        z20.check_request(report(8, 0xEA, 0x02, z20.READ, 1))
        p = profile(9)
        p[3] = z20.WRITE
        p[7] = z20.checksum(p)
        z20.check_request(p)
        p[7] ^= 1
        with self.assertRaises(z20.Z20Error):
            z20.check_request(p)
        for n in (0, 10, 254, 255):
            p = profile(n)
            p[3] = z20.WRITE
            p[7] = z20.checksum(p)
            with self.assertRaises(z20.Z20Error):
                z20.check_request(p)

    def test_macro_writes_need_a_slot_the_checksum_and_sane_lengths(self):
        z20.check_request(report(9, 0xEA, 0x02, z20.READ, 0, 0, z20.FAIL))
        z20.check_request(report(10, 0xEA, 0x02, z20.READ, 3, 0, z20.FAIL))

        def macro(n, status=1, name_len=2, data_len=3):
            r = report(9, 0xEA, 0x02, z20.WRITE, n, 0, z20.FAIL)
            r[8], r[9:11] = name_len, b"Hi"
            r[62:64], r[64:67], r[1031] = data_len.to_bytes(2, "little"), b"\x0b\x8b\x0c", status
            r[7] = z20.checksum(r)
            return r

        z20.check_request(macro(5))
        z20.check_request(macro(100, status=0xFF))
        bad = macro(5)
        bad[7] ^= 1
        for r in (bad, macro(0), macro(101), macro(5, status=0), macro(5, name_len=51), macro(5, data_len=967)):
            with self.assertRaises(z20.Z20Error):
                z20.check_request(r)
        with self.assertRaises(z20.Z20Error):  # names are only read
            z20.check_request(report(10, 0xEA, 0x02, z20.WRITE, 3, 0, z20.FAIL))


class LiveLighting(unittest.TestCase):
    def test_led_colors_need_the_checksum(self):
        frame = z20.color_frame(None, [("w,a,s,d", "ff0000"), ("bars", "00ff00")], None)
        r = z20.color_report(frame)
        z20.check_request(r)
        self.assertEqual(bytes(r[8 + 46 * 4:8 + 47 * 4]), b"\xff\xff\x00\x00")  # W
        self.assertEqual(bytes(r[8 + 160 * 4:8 + 161 * 4]), b"\xff\x00\xff\x00")  # LeftBar1
        z20.check_request(report(6, 0xEA, 0x02, 0))  # stop
        r[7] ^= 1
        with self.assertRaises(z20.Z20Error):
            z20.check_request(r)
        with self.assertRaises(z20.Z20Error):
            z20.check_request(report(6, 0xEA, 0x02, 2))

    def test_led_names(self):
        self.assertEqual(z20.led_targets("e1,logo1,RightBar9"), [21, 192, 184])
        self.assertEqual(len(z20.led_targets("all")), len(z20.LED_NAMES))
        frame = z20.color_frame(None, [("all", "000010"), ("q", "ff8000")], 50)
        self.assertEqual(z20.colors_shown(frame)["#ff8000"], ["Q"])
        with self.assertRaises(z20.Z20Error):
            z20.led_targets("w,nosuch")

    def test_ram_blocks_only_lighting(self):
        def ram(block, sub, data=b""):
            r = report(7, 0xEA, 0x02, block, sub)
            r[8:8 + len(data)] = data
            r[7] = z20.checksum(r)
            return r

        for block in range(0x0C, 0x16):
            z20.check_request(ram(block, z20.READ))
            z20.check_request(ram(block, z20.WRITE, b"\x05\x02"))
        bad = ram(0x0C, z20.WRITE, b"\x05\x02")
        bad[7] ^= 1
        # 03-0A: the presence sensor (writing it there stops its actions), 0B: key functions,
        # 00/01: Unleash's sync previews, 02 and 16: unknown
        for r in (bad, ram(0x03, z20.WRITE, b"\x01"), ram(0x08, z20.READ), ram(0x0B, z20.WRITE), ram(0x0B, z20.READ),
                  ram(0x01, z20.WRITE), ram(0x02, z20.READ), ram(0x16, z20.READ)):
            with self.assertRaises(z20.Z20Error):
                z20.check_request(r)

    def test_ram_blocks_match_the_profile(self):
        # block sizes in RAM_BLOCKS end where the next effect starts in the profile
        ends = sorted((at, at + size) for _, at, size in z20.RAM_BLOCKS.values())
        for (_, end), (start, _) in zip(ends, ends[1:]):
            self.assertEqual(end, start)


class RamUpdate(unittest.TestCase):
    class Keyboard(z20.Keyboard):
        """Records what update_ram sends; RAM reads give zeros, key reads what was written."""
        def __init__(self):
            self.sent, self.keys = [], {}

        def read_ram(self, block):
            return bytes(128)

        def write_ram(self, block, data):
            self.sent.append(("ram", block, bytes(data[:2])))

        def call(self, request, wait):
            r = bytearray(request).ljust(z20.SIZES[request[0]], b"\0")
            z20.check_request(r)
            what = {(4, 0x07): "key", (4, 0x0C): "game keys", (7, 0x1B): "rate"}[r[0], r[3]]
            value = {"key": lambda: bytes(r[8:12]), "game keys": lambda: r[7], "rate": lambda: r[8]}[what]
            if r[4] == z20.WRITE:
                self.keys[what, r[5], r[7] if what == "key" else 0] = value()
                self.sent.append((what, r[5], r[7]) if what == "key" else (what, value()))
            stored = self.keys.get((what, r[5], r[7] if what == "key" else 0))
            answer = bytearray(64)
            if what == "key":
                answer[8:12] = stored or bytes(4)
            else:
                answer[7 if what == "game keys" else 8] = stored or 0
            return bytes(answer)

    def test_parts_go_to_ram(self):
        old = profile(1)
        new = z20.set_lighting(old, "static", [b"\x00\x00\xff"], None, None)
        new[z20.P_FN_KEYS + 45 * 4:z20.P_FN_KEYS + 46 * 4] = b"\x00\x00\x6b\x00"
        kb = self.Keyboard()
        self.assertTrue(kb.update_ram(old, new))
        self.assertEqual(kb.sent, [("ram", 0x0C, b"\x01\x00"), ("ram", 0x0D, bytes(new[z20.P_STATIC:z20.P_STATIC + 2])),
                                   ("key", 1, 45)])

    def test_name_game_keys_and_rate(self):
        old = profile(1)
        new = z20.set_game_keys(z20.set_profile_name(old, "Games"), ["win", "alt-tab"])
        new[z20.P_RATE] = z20.RATES[4000]
        kb = self.Keyboard()
        self.assertTrue(kb.update_ram(old, new))
        self.assertEqual(kb.sent, [("game keys", 0xBE), ("rate", 0)])  # the name needs nothing

    def test_other_changes_need_a_reload(self):
        old = profile(1)
        reserved = bytearray(old)
        reserved[140] ^= 1  # a reserved byte
        for new in (reserved, z20.set_sensor(old, ["leave", "lock"])):  # the sensor: never through RAM
            kb = self.Keyboard()
            self.assertFalse(kb.update_ram(old, new))
            self.assertEqual(kb.sent, [])


class Sensor(unittest.TestCase):
    def test_settings_as_profile_1_has_them(self):
        p = profile(1)
        p[152:183] = bytes.fromhex("01b0040000ffff0a000300ff001e00ff001f00ff002000ff0021001600881300"[:62])
        self.assertEqual(z20.sensor_settings(p), {
            "on": True, "distance_cm": 120.0, "come": "nothing", "come_after_s": 0.0, "leave": "dark",
            "leave_after_s": 10, "welcome": "thunder", "welcome_ms": 5000})

    def test_changes_touch_only_the_sensor(self):
        p = profile(1)
        q = p
        for words in (["distance", "45"], ["leave", "lock", "30"], ["come", "wake", "2"],
                      ["welcome", "rows", "3000"], ["off"]):
            q = z20.set_sensor(q, words)
        self.assertEqual({i for i in range(len(p)) if p[i] != q[i]} - set(range(152, 183)), set())
        s = z20.sensor_settings(q)
        self.assertEqual((s["on"], s["distance_cm"], s["leave"], s["leave_after_s"], s["come"], s["come_after_s"],
                          s["welcome"], s["welcome_ms"]), (False, 45.0, "lock", 30, "wake", 2.0, "rows", 3000))

    def test_out_of_range(self):
        for words in (["distance", "5"], ["distance", "200"], ["leave", "fly"], ["leave", "dark", "5"],
                      ["come", "wake", "11"], ["welcome", "nosuch"], ["on", "now"], ["distance"]):
            with self.assertRaises(z20.Z20Error, msg=words):
                z20.set_sensor(profile(1), words)

    def test_interface_events(self):
        self.assertEqual(z20.interface_event(bytes([3, 3, 1, 0, 0, 0])), "keyboard: Game Mode 1")
        self.assertEqual(z20.interface_event(bytes([2, 0xCD, 0])), "media key PlayPause")

    def test_waiting_for_an_event_passes_over_media_keys(self):
        import contextlib
        import io
        import tempfile
        import threading
        import time
        with tempfile.TemporaryDirectory() as d:
            fifo = os.path.join(d, "hidraw")  # stands in for the keyboard's interface 1
            os.mkfifo(fifo)

            def keyboard():
                with open(fifo, "wb", buffering=0) as f:
                    for report in (bytes([2, 0xE9, 0]), bytes([2, 0, 0]), bytes([3, 3, 1, 0, 0, 0])):
                        f.write(report)  # volume up, key up, Game Mode on
                        time.sleep(0.1)
            threading.Thread(target=keyboard, daemon=True).start()
            find, z20.find_keyboard = z20.find_keyboard, lambda: (fifo, None)
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out):
                    z20.watch_events(True, wait=5)
            finally:
                z20.find_keyboard = find
            self.assertEqual(out.getvalue(), '{"event": "Game Mode", "value": 1}\n')


class PresenceService(unittest.TestCase):
    def test_leave_and_come_after_their_times(self):
        p = z20.Presence(leave_after=30, come_after=1)
        events = [(t, p.update(near, t)) for t, near in ((0, True), (5, False), (20, True), (21, False),
                                                        (50, False), (51, False), (60, True), (60.5, True),
                                                        (61, True), (62, True))]
        # away 5-20 is too short; away from 21 counts after 30 s; near from 60 counts after 1 s
        self.assertEqual([(t, e) for t, e in events if e], [(51, "leave"), (61, "come")])

    def test_the_sensors_answer(self):
        kb = z20.Keyboard.__new__(z20.Keyboard)  # no device: only the answer
        kb.general = lambda command: bytes.fromhex("04 ea 02 41 01 00 c0 41 02 02 01 00 01 01 01 01 01")
        self.assertEqual(kb.distance(), (577, ["far", "near", "nothing", "near", "near", "near", "near", "near"]))

    def test_in_view(self):
        verdicts = lambda text: [{"0": "nothing", "1": "near", "2": "far"}[c] for c in text]
        # as recorded: sitting with a weak echo, sitting, out of the beam, leaning back with one stray echo
        for text, view, newest in (("00100100", True, "near"), ("11111111", True, "near"), ("21111111", True, "far"),
                                   ("00000000", False, "nothing"), ("00000010", False, "near")):
            self.assertEqual((z20.in_view(verdicts(text)), z20.newest_echo(verdicts(text))), (view, newest), text)

    def test_nothing_in_view_holds_present_or_away(self):
        near, far = (380, ["near"] * 8), (700, ["far"] * 8)
        nothing = (45, ["nothing"] * 8)  # the distance then drifts to a few cm and means nothing
        # s: sitting 10, leaning back out of view 60 (no leave), gone 35 (leave after 30), the sensor
        # losing the chair 10 (no come: 45 mm would have been "near"), back 5 (come after 1)
        readings = iter([near] * 20 + [nothing] * 120 + [far] * 70 + [nothing] * 20 + [near] * 10)
        clock = [0.0]

        class Keyboard:
            def distance(self):
                try:
                    return next(readings)
                except StopIteration:
                    raise KeyboardInterrupt from None

            def profile_number(self):
                return 1

            def read_profile(self, n):
                return None

            def close(self):
                pass
        cfg = z20.presence_config("presence.ini", "[presence]\nleave = lock\ncome = wake\n")
        saved = (z20.Keyboard, z20.presence_config, z20.sensor_settings, z20.time.monotonic, z20.time.sleep,
                 z20.Desktop.do, z20.Desktop.log)
        done = []
        try:
            z20.Keyboard, z20.presence_config = Keyboard, lambda: cfg
            z20.sensor_settings = lambda p: {"distance_cm": 50.0}
            z20.time.monotonic = lambda: clock[0]
            z20.time.sleep = lambda s: clock.__setitem__(0, clock[0] + s)
            z20.Desktop.do = lambda self, action: done.append((clock[0], action))
            z20.Desktop.log = lambda self, text: None
            with self.assertRaises(KeyboardInterrupt):
                z20.presence(dry_run=True)
        finally:
            (z20.Keyboard, z20.presence_config, z20.sensor_settings, z20.time.monotonic, z20.time.sleep,
             z20.Desktop.do, z20.Desktop.log) = saved
        self.assertEqual(done, [(100.0, "lock"), (116.0, "wake")])

    def test_config(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "presence.ini")
            self.assertEqual(z20.presence_config(path)["leave"], [("pause-media", 0)])  # no file: defaults
            with open(path, "w") as f:
                f.write("[presence]\nleave after = 20\ndistance = 45\nleave = lock, pause-media, screen-off after 60\n"
                        "come = wake\nleave run = notify-send 'bye, see you'\n")
            cfg = z20.presence_config(path)
            self.assertEqual((cfg["leave_after"], cfg["come_after"], cfg["distance_mm"], cfg["leave"], cfg["come"],
                              cfg["leave_run"], cfg["come_run"]),
                             (20.0, 1.0, 450, [("lock", 0), ("pause-media", 0), ("screen-off", 60)], [("wake", 0)],
                              "notify-send 'bye, see you'", ""))
            for bad in ("lock, explode", "screen-off after", "screen-off after soon", "lock after -1"):
                with open(path, "w") as f:
                    f.write(f"[presence]\nleave = {bad}\n")
                with self.assertRaises(z20.Z20Error, msg=bad):
                    z20.presence_config(path)

    def test_away_light(self):
        cfg = lambda text: z20.presence_config("presence.ini", "[presence]\n" + text)
        self.assertEqual(cfg("")["away_light"], [])
        self.assertEqual(cfg("away light = animate fire ff0000 --cycle 800\n")["away_light"],
                         ["animate", "fire", "ff0000", "--cycle", "800"])
        self.assertEqual(cfg("away light = light off\n")["away_light"], ["light", "off"])
        for bad in ("fire", "light", "light fire", "animate wave", "light reload", "animate fire --save",
                    "light static ff0000 --live", "light static 'ff0000"):
            with self.assertRaises(z20.Z20Error, msg=bad):
                cfg(f"away light = {bad}\n")

    def test_set_changes_only_what_it_sets(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "z20", "presence.ini")
            z20.set_presence([("leave", "lock")], path)  # no file yet
            with open(path) as f:
                self.assertEqual(f.read(), "[presence]\nleave = lock\n")
            with open(path, "w") as f:
                f.write("# mine\n[presence]\n# distance = 45\nLeave After = 30\nleave = lock,\n  pause-media\n"
                        "  # a note\ncome = wake\n\n[other]\nleave = x\n")
            z20.set_presence([("leave", ""), ("away light", "animate fire"), ("leave after", "20")], path)
            with open(path) as f:
                self.assertEqual(f.read(), "# mine\n[presence]\n# distance = 45\nleave after = 20\nleave =\n"
                                           "  # a note\ncome = wake\naway light = animate fire\n\n[other]\nleave = x\n")
            cfg = z20.presence_config(path)
            self.assertEqual((cfg["leave"], cfg["leave_after"], cfg["away_light"]), ([], 20.0, ["animate", "fire"]))
            for bad in ([("leave", "explode")], [("nonsense", "1")], [("leave run", "a\nb")],
                        [("away light", "light reload")]):
                with self.assertRaises(z20.Z20Error, msg=bad):
                    z20.set_presence(bad, path)
            with open(path) as f:
                self.assertIn("leave =\n", f.read())  # nothing written

    def test_changes_at_the_same_time_all_land(self):
        import tempfile
        import threading
        changes = [("leave after", "20"), ("come after", "2"), ("leave", "lock"), ("come", "wake"),
                   ("distance", "40"), ("away light", "light off")]
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "presence.ini")
            start = threading.Barrier(len(changes))

            def change(key, value):
                start.wait()
                z20.set_presence([(key, value)], path)
            threads = [threading.Thread(target=change, args=c) for c in changes]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            cfg = z20.presence_config(path)
            self.assertEqual((cfg["leave_after"], cfg["come_after"], cfg["leave"], cfg["come"], cfg["distance_mm"],
                              cfg["away_light"]),
                             (20.0, 2.0, [("lock", 0)], [("wake", 0)], 400, ["light", "off"]))

    def test_away_light_and_back(self):
        class Desktop(z20.Desktop):
            def __init__(self):
                super().__init__()
                self.calls, self.logged = [], []

            def act(self, argv):
                self.calls.append(argv[2:])

            def log(self, text):
                self.logged.append(text)

        desktop = Desktop()
        desktop.away_light(["light", "breathing", "0040ff", "000000"])
        desktop.away_light(["animate", "fire"])
        desktop.lighting_back()
        self.assertEqual(desktop.calls, [["animate", "off", "--live"],
                                         ["light", "breathing", "0040ff", "000000", "--live"],
                                         ["animate", "fire", "--live"], ["animate", "reload"], ["light", "reload"]])
        self.assertEqual(desktop.logged, ["  away light: light breathing 0040ff 000000", "  away light: animate fire",
                                          "  lighting back"])

    def test_delayed_actions_and_coming_back_early(self):
        p = z20.Pending()
        p.set([("lock", 0), ("screen-off", 60)], now=100)
        self.assertEqual((p.due(100), p.due(130), p.due(160)), (["lock"], [], ["screen-off"]))
        p.set([("lock", 0), ("screen-off", 60)], now=200)
        self.assertEqual(p.due(200), ["lock"])
        p.set([("wake", 0)], now=230)  # back before the screen went off
        self.assertEqual((p.due(230), p.due(300)), (["wake"], []))

    def test_resume_only_what_was_paused(self):
        class Desktop(z20.Desktop):
            def __init__(self):
                super().__init__()
                self.state = {"org.mpris.MediaPlayer2.a": "Playing", "org.mpris.MediaPlayer2.b": "Paused"}
                self.calls, self.logged = [], []

            def query(self, *args):
                if args[0] == "call":
                    return "as 3 " + " ".join(f'"{n}"' for n in [":1.5", *self.state])
                return f's "{self.state[args[1]]}"'

            def act(self, argv):
                self.calls.append((argv[3], argv[-1]))

            def log(self, text):
                self.logged.append(text)

        desktop = Desktop()
        desktop.do("pause-media")
        self.assertEqual(desktop.calls, [("org.mpris.MediaPlayer2.a", "Pause")])
        desktop.calls = []
        desktop.do("resume-media")
        self.assertEqual(desktop.calls, [("org.mpris.MediaPlayer2.a", "Play")])
        desktop.calls = []
        desktop.do("resume-media")  # nothing paused any more
        self.assertEqual(desktop.calls, [])
        self.assertEqual(desktop.logged, ["  pause-media: paused a", "  resume-media: resumed a",
                                          "  resume-media: resumed nothing"])


class GeneralSettings(unittest.TestCase):
    def test_game_mode_keys_are_kept_inverted(self):
        p = profile(1)
        p[z20.P_GAME_KEYS] = 0xBF  # as profile 1 has it: only the Win key blocked
        self.assertEqual(z20.game_keys(p), ["win"])
        self.assertEqual(z20.set_game_keys(p, ["win", "alt-tab"])[z20.P_GAME_KEYS], 0xBE)
        self.assertEqual(z20.game_keys(z20.set_game_keys(p, [])), [])

    def test_report_rate(self):
        p = profile(1)
        p[z20.P_RATE] = 2
        self.assertEqual(z20.rate_hz(p), 1000)
        def rate(sub, value=0):
            r = report(7, 0xEA, 0x02, 0x1B, sub, 0, 0, 0, value)
            r[7] = z20.checksum(r)
            return r
        for r in (rate(z20.READ), rate(2), rate(z20.WRITE, 0), rate(z20.WRITE, 2)):
            z20.check_request(r)
        bad = rate(z20.WRITE, 1)
        bad[7] ^= 1
        for r in (bad, rate(z20.WRITE, 3)):  # 3 would be 8000 Hz, which Unleash doesn't offer for the Z20
            with self.assertRaises(z20.Z20Error):
                z20.check_request(r)

    def test_nkro_switch(self):
        z20.check_request(report(4, 0xEA, 0x02, 0x0F, z20.WRITE, 0, 0, 1))
        with self.assertRaises(z20.Z20Error):
            z20.check_request(report(4, 0xEA, 0x02, 0x0F, z20.WRITE, 0, 0, 2))

    def test_profile_name_and_factory_parts(self):
        p = z20.set_profile_name(profile(3), "Spiele")
        self.assertEqual(z20.profile_name(p), "Spiele")
        self.assertEqual(p[z20.P_NAME + 12:z20.P_NAME + 14], b"\xff\xff")
        with self.assertRaises(z20.Z20Error):
            z20.set_profile_name(p, "x" * 64)
        factory = bytearray(profile(254))
        for i in range(8, len(factory)):
            factory[i] = (factory[i] + 1) & 0xFF
        q = z20.from_factory(p, factory, z20.FACTORY_LIGHTING)
        expected = {*range(1288, 1290), *range(1320, 1597)}
        self.assertEqual({i for i in range(len(p)) if p[i] != q[i]}, expected)

    def test_events(self):
        self.assertIsNone(z20.keyboard_event(bytes([1, 1, 0, 0])))  # a macro's mouse click
        self.assertEqual(z20.keyboard_event(bytes([3, 0, 2, 0, 0, 0])), {"event": "profile", "value": 2})
        self.assertEqual(z20.keyboard_event(bytes([2, 0xE9, 0])), {"event": "media key", "key": "VolumeUp"})


class Answers(unittest.TestCase):
    def test_answer_must_belong_to_the_read(self):
        ask = report(8, 0xEA, 0x02, z20.READ, 1)
        z20.check_answer(ask, report(8, 0xEA, 0x02, z20.READ, 1, 0, z20.SUCCESS))
        with self.assertRaises(z20.Z20Error):  # another process asked for profile 2 in between
            z20.check_answer(ask, report(8, 0xEA, 0x02, z20.READ, 2, 0, z20.SUCCESS))
        ask = report(4, 0xEA, 0x02, 0x06, z20.READ)
        with self.assertRaises(z20.Z20Error):  # the answer to a Game Mode read
            z20.check_answer(ask, report(4, 0xEA, 0x02, 0x0B, z20.READ, 0, z20.SUCCESS))

    def test_refused_and_written(self):
        ask = report(4, 0xEA, 0x02, 0x0B, z20.WRITE, 0, 0, 1)
        z20.check_answer(ask, report(4, 0xEA, 0x02, 0x0B, z20.WRITE, 0, z20.SUCCESS, 1))
        with self.assertRaises(z20.Z20Error):
            z20.check_answer(ask, report(4, 0xEA, 0x02, 0x0B, z20.WRITE, 0, z20.FAIL, 1))


class Reports(unittest.TestCase):
    def test_checksum_makes_the_sum_zero(self):
        p = profile()
        self.assertEqual((sum(p[8:]) + p[7]) & 0xFF, 0)

    def test_macro_actions(self):
        data = bytes([0x01, 39, 0, 0x1A, 0x9A, 0x7A, 0xFA, 0x03, 0xE9, 0x00, 0x03, 0, 0,
                      0x70, 0xF0, 0x78, 0xF8, 0x80, 0x10, 0x00, 0x20, 0x00])
        self.assertEqual(z20.macro_actions(data), [
            "wait 20 ms", "W down", "W up", "left button down", "left button up", "VolumeUp down",
            "media up", "LCtrl down", "LCtrl up", "wheel down", "wheel up", "mouse to 16 32"])

    def test_steps_read_back_as_written(self):
        # each step after a wait, as Unleash writes them: W, left button, VolumeUp, LCtrl, wheel,
        # mouse to 16 32, Comma, KPPlus, F14, KP7, RGUI
        steps = [[0x1A], [0x9A], [0x7A], [0xFA], [0x03, 0xE9, 0x00], [0x03, 0, 0], [0x70], [0xF0], [0x78],
                 [0xF8], [0x80, 0x10, 0x00, 0x20, 0x00], [0x36], [0xB6], [0x57], [0xD7], [0x69], [0xE9],
                 [0x5F], [0xDF], [0x77], [0xF7]]
        data = b"".join(bytes([0x01, 39 if i % 2 else 4, 0, *s]) for i, s in enumerate(steps))
        self.assertEqual(z20.parse_steps(", ".join(z20.macro_actions(data))), data)

    def test_steps(self):
        def steps(text):  # what parse_steps gives, without the 2.5 ms waits it puts before each step
            return z20.parse_steps(text).replace(z20.MACRO_GAP, b"")

        self.assertEqual(z20.parse_steps("H"), bytes([0x01, 4, 0, 0x0B, 0x01, 4, 0, 0x8B]))
        self.assertEqual(z20.parse_steps("wait 20, H down"), bytes([0x01, 39, 0, 0x0B]))
        self.assertEqual(steps("LShift down, H, LShift up, I"), bytes([0x71, 0x0B, 0x8B, 0xF1, 0x0C, 0x8C]))
        self.assertEqual(steps("ctrl down, c, ctrl up"), bytes([0x70, 0x06, 0x86, 0xF0]))
        self.assertEqual(steps("left click, wait 2.5 ms, right button down"), bytes([0x7A, 0xFA, 0x7B]))
        self.assertEqual(steps("playpause"), bytes([0x03, 0xCD, 0x00, 0x03, 0x00, 0x00]))
        self.assertEqual(steps("wait 0.5"), bytes([0x01, 0, 0]))
        self.assertEqual(steps("wait 40000"), bytes([0x01, 0xFF, 0xFF, 0x01, 0x7F, 0x38]))  # 32768 + 7232 ms
        for bad in ("", "W,, E", "wait 0", "wait x", "f21", "wheel", "media down", "nosuchkey down",
                    "mouse to 1 2 3", "key 0x01", ", ".join(["W"] * 500)):
            with self.assertRaises(z20.Z20Error, msg=bad):
                steps(bad)

    def test_key_functions(self):
        names = {1: "Autorunner"}
        self.assertEqual(z20.key_function(bytes([3, 1, 8, 0]), names)[0],
                         'macro 1 "Autorunner" (loop until pressed again)')
        self.assertEqual(z20.key_function(bytes([0, 0x05, 0x1A, 0]), names)[0], "key LCtrl+LAlt+W")
        self.assertEqual(z20.key_function(bytes([2, 0xCD, 0, 0]), names)[0], "media PlayPause")
        self.assertEqual(z20.key_function(bytes([7, 0, 0, 0]), names)[0], "left click")
        self.assertEqual(z20.key_function(bytes([0xFF] * 4), names)[0], "disabled")

    def test_macro_run_modes(self):
        # checked on the keyboard: mode 11 with count 1 runs twice, with count 3 four times
        self.assertEqual(z20.key_function(bytes([3, 2, 11, 1]), {})[0], "macro 2 (2 times)")
        self.assertEqual(z20.key_function(bytes([3, 2, 11, 3]), {})[0], "macro 2 (4 times)")
        self.assertEqual(z20.key_function(bytes([3, 2, 9, 0]), {})[0], "macro 2 (once)")
        self.assertEqual(z20.key_function(bytes([3, 2, 12, 0]), {})[0], "macro 2 (while held)")

    def test_key_functions_from_words(self):
        parse = z20.parse_function
        self.assertEqual(parse(["macro", "2"], [1, 2], (11, 1)), bytes([3, 2, 11, 1]))
        self.assertEqual(parse(["macro", "2"], [2], (8, 0)), bytes([3, 2, 8, 0]))
        self.assertEqual(parse(["key", "ctrl+shift+t"], [], None), bytes([0, 0x03, 0x17, 0]))
        self.assertEqual(parse(["key", "F5"], [], None), bytes([0, 0, 0x3E, 0]))
        self.assertEqual(parse(["key", "super"], [], None), bytes([0, 0x08, 0, 0]))
        self.assertEqual(parse(["media", "playpause"], [], None), bytes([2, 0xCD, 0, 0]))
        self.assertEqual(parse(["click", "right"], [], None), bytes([8, 0, 0, 0]))
        self.assertEqual(parse(["wheel", "down"], [], None), bytes([6, 1, 0, 0]))
        self.assertEqual(parse(["profile", "3"], [], None), bytes([19, 0, 0, 0]))
        self.assertEqual(parse(["profile", "next"], [], None), bytes([30, 0, 0, 0]))
        self.assertEqual(parse(["off"], [], None), bytes([0xFF, 0, 0, 0]))
        for words, slots in ((["macro", "7"], [1, 2]), (["macro"], [1]), (["key", "ctrl+nosuchkey"], []),
                             (["key", "a+b+c"], []), (["media", "loud"], []), (["off", "now"], [])):
            with self.assertRaises(z20.Z20Error, msg=words):
                parse(words, slots, (11, 1))

    def test_key_names(self):
        self.assertEqual(len(set(z20.KEY_POSITIONS.values())), len(z20.KEY_POSITIONS))
        for name, pos in (("capslock", 66), ("E1", 21), ("grave", 22), ("Comma", 91), ("win", 104),
                          ("y", 50), ("game", 0), ("q", 45)):
            self.assertEqual(z20.key_target(name, False), pos, name)
        self.assertEqual(z20.key_target("q", True), 45)
        for name, fn in (("fn", False), ("fn", True), ("1", True), ("up", True), ("ralt", True), ("nosuch", False)):
            with self.assertRaises(z20.Z20Error, msg=name):
                z20.key_target(name, fn)

    def test_all_keys_back_to_factory_but_win_and_fn(self):
        p, factory = profile(1), bytearray(profile(254))
        for i in range(z20.P_KEYS, z20.P_FN_KEYS + 121 * 4):
            factory[i] = (factory[i] + 1) & 0xFF
        q = z20.reset_keys(p, factory)
        keep = {base + pos * 4 + i for base in (z20.P_KEYS, z20.P_FN_KEYS) for pos in (104, 108) for i in range(4)}
        for i in range(len(p)):
            in_tables = z20.P_KEYS <= i < z20.P_FN_KEYS + 121 * 4
            self.assertEqual(q[i], factory[i] if in_tables and i not in keep else p[i], i)

    def test_changed_keys(self):
        factory = profile(254)
        p = bytearray(factory)
        p[z20.P_KEYS + 66 * 4:z20.P_KEYS + 67 * 4] = b"\x00\x01\x00\x00"
        p[z20.P_FN_KEYS + 45 * 4 + 2] ^= 1
        p[z20.P_KEYS + 21 * 4] ^= 1  # E1, skipped
        self.assertEqual([label for label, _ in z20.changed_keys(p, factory, skip=z20.E_KEYS.values())],
                         ["Fn+Q", "CapsLock"])

    def test_profile_name(self):
        p = profile()
        name = "DEFAULT 1".encode("utf-16-le")
        p[8:10] = (9).to_bytes(2, "little")
        p[10:10 + len(name)] = name
        self.assertEqual(z20.profile_name(p), "DEFAULT 1")


class Lighting(unittest.TestCase):
    def test_static_changes_only_the_effect_and_its_color(self):
        p = profile()
        q = z20.set_lighting(p, "static", [b"\x12\x34\x56"], 50, None)
        self.assertEqual(changed(p, q) - {1288, 1289, 1336, 1337, 1338, 1339}, set())
        self.assertEqual((q[1288], bytes(q[1336:1340])), (1, b"\x80\x12\x34\x56"))
        self.assertEqual(z20.lighting(q), {"effect": "static", "colors": ["#123456"], "brightness": 50})

    def test_breathing_keeps_the_hold_percentages(self):
        p = profile()
        q = z20.set_lighting(p, "breathing", [b"\x00\xff\x00", b"\x00\x00\x00"], None, 4000)
        self.assertEqual(changed(p, q) - {1288, 1289, 1356, 1357, 1360, 1361, 1362, 1365, 1366, 1367}, set())
        self.assertEqual(z20.lighting(q), {"effect": "breathing", "colors": ["#00ff00", "#000000"], "cycle_ms": 4000,
                                           "brightness": round(p[z20.P_BREATHING + 19] * 100 / 255)})  # as it was

    def test_effects_keep_their_stored_colors(self):
        p = profile()
        q = z20.set_lighting(p, "wave", [], None, None)
        self.assertEqual(changed(p, q) - {1288, 1289}, set())
        self.assertEqual((q[1288], q[1289]), (5, p[z20.P_WAVE + 4]))  # the wave's own direction

    def test_colors_fill_the_effect(self):
        red, blue = b"\xff\x00\x00", b"\x00\x00\xff"
        self.assertEqual(z20.fill_colors("wave", [red, blue]), [red, blue] * 4)
        self.assertEqual(len(z20.fill_colors("rows", [red])), 7)
        self.assertEqual(z20.fill_colors("breathing", [red]), [red, b"\0\0\0"])
        self.assertEqual(z20.fill_colors("static", [red]), [red])
        self.assertEqual(z20.fill_colors("wave", []), [])  # the stored ones

    def test_direction(self):
        q = z20.set_lighting(profile(), "wave", [], None, None, "left")
        self.assertEqual((q[z20.P_WAVE + 4], q[z20.P_EFFECT + 1]), (3, 3))
        q = z20.set_lighting(profile(), "spiral", [], None, None, "ccw")
        self.assertEqual((q[z20.P_SPIRAL + 3], q[z20.P_EFFECT + 1]), (1, 1))

    def test_off(self):
        q = z20.set_lighting(profile(), "off", [], None, None)
        self.assertEqual(z20.lighting(q), {"effect": "off"})



class Animate(unittest.TestCase):
    def test_every_led_has_a_place(self):
        for iso, missing in ((True, {57}), (False, {119, 120})):  # ANSI \\ or ISO # and \\
            layout = z20.led_layout(iso)
            self.assertEqual(set(z20.LED_NAMES) - set(layout), {116, 117, *missing})  # 116-117: scroll wheel
            spots = sorted(layout.values())
            for a, b in zip(spots, spots[1:]):
                self.assertGreater(abs(a[0] - b[0]) + abs(a[1] - b[1]), 0.4, (a, b))
        layout = z20.led_layout()
        self.assertEqual(layout[z20.KEY_BY_NAME["esc"]], (1.75, 0.5))
        self.assertEqual(layout[z20.KEY_BY_NAME["space"]], (1.25 + 3.75 + 3.125, 6))

    def test_effects_give_colors_and_frames_the_keyboard_takes(self):
        import random
        layout = z20.led_layout()
        for effect, (colors, most, cycle) in z20.ANIMATIONS.items():
            colors_at = z20.animation(effect, [tuple(z20.parse_color(c)) for c in colors], cycle, layout,
                                      random.Random(7))
            lit = set()
            for i in range(100):
                frame = colors_at(i * z20.FRAME_S)
                self.assertEqual(set(frame), set(layout), effect)
                self.assertTrue(all(0 <= c <= 255 for color in frame.values() for c in color), effect)
                lit |= {p for p, color in frame.items() if max(color) > 1}
                z20.check_request(z20.color_report(z20.animation_frame(frame, 0xFF)))
            self.assertGreater(len(lit), len(layout) // 3, effect)  # it moves across the keyboard

    def test_blend(self):
        red, blue = (255, 0, 0), (0, 0, 255)
        self.assertEqual(z20.blend([red, blue], 0), red)
        self.assertEqual(z20.blend([red, blue], 1), blue)
        self.assertEqual(z20.blend([red, blue], 0.5), (127.5, 0, 127.5))
        self.assertEqual(z20.blend([red, blue], 1, cyclic=True), red)
        self.assertEqual(z20.blend([red, blue], 0.75, cyclic=True), (127.5, 0, 127.5))

    def test_saved_settings_live_before_saved(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            config, live = os.path.join(d, "animation.ini"), os.path.join(d, "live.ini")
            old = z20.ANIMATION_CONFIG, z20.ANIMATION_LIVE
            z20.ANIMATION_CONFIG, z20.ANIMATION_LIVE = config, live
            try:
                self.assertIsNone(z20.saved_animation())
                z20.write_animation(config, "fire", ["ff0000", "ffff00"], 900, None)
                self.assertEqual(z20.saved_animation(), ("fire", ["ff0000", "ffff00"], 900, None, "saved"))
                z20.write_animation(live, "gradient", ["00ff00"], None, 40)
                self.assertEqual(z20.saved_animation(), ("gradient", ["00ff00"], None, 40, "live"))
                with open(config, "w") as f:
                    f.write("[animation]\neffect = lava\n")
                os.remove(live)
                with self.assertRaises(z20.Z20Error):
                    z20.saved_animation()
            finally:
                z20.ANIMATION_CONFIG, z20.ANIMATION_LIVE = old

    def test_checks(self):
        z20.check_animation("rain", ["00ff00", "ffffff"], 1500, 80)
        for effect, colors, cycle, brightness in (("lava", [], None, None), ("scanner", ["ff0000", "00ff00"], None, None),
                                                  ("fire", ["red"], None, None), ("fire", [], 50, None),
                                                  ("fire", [], None, 101)):
            with self.assertRaises(z20.Z20Error, msg=effect):
                z20.check_animation(effect, colors, cycle, brightness)

    def test_state_of_a_process_that_ended(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            old = z20.ANIMATION_STATE
            z20.ANIMATION_STATE = os.path.join(d, "animation.json")
            try:
                self.assertIsNone(z20.animation_state())
                z20.save_json(z20.ANIMATION_STATE, {"pid": os.getpid(), "effect": "fire"})
                self.assertIsNone(z20.animation_state())  # this process isn't a z20 animate
            finally:
                z20.ANIMATION_STATE = old


class Backlight(unittest.TestCase):
    class Keyboard:
        """The lighting in RAM as a profile puts it there (padded blocks); records which blocks are written."""
        def __init__(self, p):
            self.ram, self.written = {}, []
            self.load(p)

        def load(self, p):  # as a reload or profile switch does
            self.ram[z20.RAM_EFFECT] = bytes(p[z20.P_EFFECT:z20.P_EFFECT + 2]).ljust(128, b"\x99")
            for block, at, size in z20.RAM_BLOCKS.values():
                self.ram[block] = bytes(p[at:at + size]).ljust(128, b"\x99")

        def read_ram(self, block):
            return self.ram[block]

        def write_ram(self, block, data):
            self.written.append(block)
            self.ram[block] = bytes(data)

    def block(self, kb, effect):
        block, _, size = z20.RAM_BLOCKS[effect]
        return kb.ram[block][:size]

    def brightness(self, kb, effect):
        at = z20.RAM_BLOCKS[effect][1]
        return [self.block(kb, effect)[i - at] for i in z20.BRIGHTNESS_AT[effect]]

    def test_only_brightness_bytes(self):
        p = profile(1)
        for effect, (_, at, size) in z20.RAM_BLOCKS.items():
            block = bytes(p[at:at + size])
            spots = {i - at for i in z20.BRIGHTNESS_AT[effect]}
            self.assertTrue(spots and all(0 <= i < size for i in spots), effect)
            self.assertEqual(z20.dimmed(block, effect, 100), block)
            self.assertEqual(changed(z20.dimmed(block, effect, 0), block), {i for i in spots if block[i]}, effect)
        self.assertIn(z20.P_PULSE + 21, z20.BRIGHTNESS_AT[3])  # pulse's background color goes dark too
        frame = z20.color_frame(None, [("all", "ff8000")], 80)
        self.assertEqual(z20.dimmed_frame(frame, 50)[:8], bytes([102, 0xFF, 0x80, 0, 102, 0xFF, 0x80, 0]))

    def test_dims_the_running_effect_and_brings_it_back(self):
        p = z20.set_lighting(profile(1), "wave", [], 100, None)
        kb, dimmer = self.Keyboard(p), z20.Dimmer()
        dimmer.apply(kb, 50)
        self.assertEqual(self.brightness(kb, 5), [128] * 8)
        self.assertEqual(changed(self.block(kb, 5), p[z20.P_WAVE:z20.P_WAVE + 51]),
                         {i - z20.P_WAVE for i in z20.BRIGHTNESS_AT[5]})
        self.assertEqual(kb.ram[0x11][51:], b"\x99" * 77)  # the rest of the block as it was
        dimmer.apply(kb, 50)
        dimmer.apply(kb, 0)
        self.assertEqual((kb.written, self.brightness(kb, 5)), ([0x11, 0x11], [0] * 8))
        dimmer.apply(kb, 100)
        self.assertEqual(self.block(kb, 5), p[z20.P_WAVE:z20.P_WAVE + 51])

    def test_a_new_lighting_is_dimmed_as_set(self):
        p = z20.set_lighting(profile(1), "wave", [], 100, None)
        kb, dimmer = self.Keyboard(p), z20.Dimmer()
        dimmer.apply(kb, 50)
        kb.load(z20.set_lighting(p, "wave", [], 60, None))  # z20 light wave --brightness 60, a reload
        dimmer.apply(kb, 50)
        self.assertEqual(self.brightness(kb, 5), [76] * 8)  # half of 153, not of 128
        dimmer.apply(kb, 100)
        self.assertEqual(self.brightness(kb, 5), [153] * 8)

    def test_an_effect_left_behind_gets_its_block_back(self):
        p = z20.set_lighting(z20.set_lighting(profile(1), "static", [b"\xff\x00\x00"], 100, None), "wave", [], 100, None)
        kb, dimmer = self.Keyboard(p), z20.Dimmer()
        dimmer.apply(kb, 50)
        kb.ram[z20.RAM_EFFECT] = b"\x01\x00".ljust(128, b"\x99")  # the Fn keys switch to static
        dimmer.apply(kb, 50)
        self.assertEqual(self.block(kb, 5), p[z20.P_WAVE:z20.P_WAVE + 51])
        self.assertEqual(self.brightness(kb, 1), [128])
        kb.ram[z20.RAM_EFFECT] = b"\x00\x00".ljust(128, b"\x99")  # off: nothing to dim
        dimmer.apply(kb, 50)
        self.assertEqual(self.brightness(kb, 1), [255])
        self.assertEqual(dimmer.state(), {"effect": None, "block": None, "shown": None})

    def test_resumes_what_a_killed_one_dimmed(self):
        p = z20.set_lighting(profile(1), "wave", [], 100, None)
        kb, dimmer = self.Keyboard(p), z20.Dimmer()
        dimmer.apply(kb, 30)
        again = z20.Dimmer()
        again.resume(dimmer.state())
        again.apply(kb, 100)
        self.assertEqual(self.block(kb, 5), p[z20.P_WAVE:z20.P_WAVE + 51])

    def test_shown_as_set(self):
        p = z20.set_lighting(profile(1), "wave", [], 100, None)
        kb, dimmer = self.Keyboard(p), z20.Dimmer()
        dimmer.apply(kb, 20)
        old = z20.backlight_state
        z20.backlight_state = lambda: {"pid": 1, "percent": 20, **dimmer.state()}
        try:
            self.assertEqual(z20.lighting(z20.with_ram_lighting(kb, profile(1), 5))["brightness"], 100)
            kb.load(z20.set_lighting(p, "wave", [], 60, None))  # changed since: RAM as it is
            self.assertEqual(z20.lighting(z20.with_ram_lighting(kb, profile(1), 5))["brightness"], 60)
        finally:
            z20.backlight_state = old

    def test_without_it_full_brightness(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            old = z20.BACKLIGHT_STATE
            z20.BACKLIGHT_STATE = os.path.join(d, "z20-backlight.json")
            try:
                self.assertEqual(z20.backlight_percent(), 100)
                z20.save_json(z20.BACKLIGHT_STATE, {"pid": os.getpid(), "percent": 0})
                self.assertEqual(z20.backlight_percent(), 100)  # this process isn't a z20 backlight
            finally:
                z20.BACKLIGHT_STATE = old

    def test_its_own_level(self):
        import signal
        import tempfile
        told, calls = [], []
        old = (z20.BACKLIGHT_LEVEL, z20.backlight_state, z20.upower_set, z20.systemctl,
               signal.signal(signal.SIGUSR2, lambda signum, frame: told.append(signum)))
        with tempfile.TemporaryDirectory() as d:
            z20.BACKLIGHT_LEVEL = os.path.join(d, "backlight.json")
            z20.backlight_state = lambda: {"pid": os.getpid(), "percent": 100, "off": False, "led": True}
            z20.upower_set = lambda path, value: calls.append(("upower", path, value)) or True
            z20.systemctl = lambda *args, check=False: calls.append(args)
            try:
                self.assertEqual(z20.backlight_level(), 100)
                self.assertEqual([z20.set_backlight(w) for w in ("up", "45", "down", "down", "0", "down")],
                                 [100, 45, 35, 25, 0, 0])
                self.assertEqual(z20.backlight_level(), 0)
                self.assertEqual(calls[1], ("upower", z20.UPOWER_KBD[1] + "/evga_z20ookbd_backlight", 45))
                self.assertEqual(len(told), 6)  # the service hears of each; none enabled it
                self.assertEqual(z20.backlight_info(), {"percent": 0, "shown": 100, "off": False, "dimmed": False,
                                                        "service": True, "led": True})
                z20.backlight_state = lambda: None
                with open(z20.BACKLIGHT_LEVEL, "w") as f:
                    f.write('{"percent": 250}')
                self.assertEqual(z20.backlight_level(), 100)
                self.assertIn("doesn't run", z20.backlight_text(z20.backlight_info()))
            finally:
                (z20.BACKLIGHT_LEVEL, z20.backlight_state, z20.upower_set, z20.systemctl, handler) = old
                signal.signal(signal.SIGUSR2, handler)

    def test_what_the_desktop_sets(self):
        # gdbus monitor on UPower; the ThinkPad puts its level back on its own, the Z20's LED has its own path
        path = b"/org/freedesktop/UPower/KbdBacklight: org.freedesktop.UPower.KbdBacklight."
        led = b"/org/freedesktop/UPower/KbdBacklight/evga_z20ookbd_backlight: org.freedesktop.UPower.KbdBacklight."
        lines = [b"The name org.freedesktop.UPower is owned by :1.43", path + b"BrightnessChanged (0,)",
                 path + b"BrightnessChangedWithSource (0, 'external')", path + b"BrightnessChanged (1,)",
                 path + b"BrightnessChangedWithSource (1, 'internal')", led + b"BrightnessChangedWithSource (0, 'external')",
                 path + b"BrightnessChangedWithSource (2, 'external')\n"]
        self.assertEqual([z20.desktop_set(line) for line in lines], [None, None, 0, None, None, None, 2])

    def test_the_screens(self):
        import subprocess

        def output(n, name, enabled, dimming):
            return (f"\x1b[01;32mOutput: \x1b[0;0m{n} {name} 6fb1ba17\n\t\x1b[01;3{2 if enabled else 1}m"
                    f"{'enabled' if enabled else 'disabled'}\x1b[0;0m\n\t\x1b[01;32mconnected\x1b[0;0m\n"
                    f"\tBrightness control: supported, set to 100% and dimming to {dimming}%\n")
        old = z20.subprocess.run
        # the laptop's own screen off and not dimmed; a third screen without brightness control
        for dimming, modes, seen in ((100, "on on", (False, 1.0)), (30, "on on", (False, 0.3)),
                                     (30, "off off", (True, 0.3)), (100, "", (False, 1.0))):
            answers = {"-o": output(1, "eDP-1", False, 100) + output(2, "DP-1", True, dimming)
                       + output(3, "DP-8", True, dimming) + "\x1b[01;32mOutput: \x1b[0;0m4 DP-10 36ef\n\tenabled\n",
                       "show": "".join(f"dpms mode for screen DP-{i}: {m}\n" for i, m in enumerate(modes.split()))}
            z20.subprocess.run = lambda argv, **kw: subprocess.CompletedProcess(argv, 0, answers[argv[-1]], "")
            try:
                self.assertEqual(z20.screens(), seen)
            finally:
                z20.subprocess.run = old

    def test_the_lid(self):
        changed = b"/org/freedesktop/UPower: org.freedesktop.DBus.Properties.PropertiesChanged ('org.freedesktop.UPower', "
        battery = (b"/org/freedesktop/UPower/devices/battery_BAT0: org.freedesktop.DBus.Properties.PropertiesChanged "
                   b"('org.freedesktop.UPower.Device', {'LidIsClosed': <true>}, @as [])")  # not the daemon's
        self.assertEqual([z20.lid_closed(line) for line in (changed + b"{'LidIsClosed': <true>}, @as [])",
                                                             changed + b"{'OnBattery': <false>, 'LidIsClosed': <false>}, @as [])",
                                                             changed + b"{'OnBattery': <true>}, @as [])", battery)],
                         [True, False, None, None])

class Commands(unittest.TestCase):
    """main() with a stand-in keyboard: what the commands print."""

    def run_z20(self, *argv):
        import contextlib
        import io

        class StandIn:
            model = "Z20 Elite ISO"

            def __init__(self, lock=True):
                pass

            def profile_number(self):
                return 2

            def read_profile(self, n):
                return z20.set_profile_name(profile(n), "Work" if n == 1 else f"DEFAULT {n}")

            def close(self):
                pass

        old = z20.Keyboard, sys.argv
        z20.Keyboard, sys.argv = StandIn, ["z20", *argv]
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                z20.main()
        finally:
            z20.Keyboard, sys.argv = old
        return out.getvalue()

    def test_profile_without_a_number_lists_them(self):
        import json
        listed = json.loads(self.run_z20("profile", "--json"))
        self.assertEqual([p["profile"] for p in listed], list(range(1, 10)))
        self.assertEqual((listed[0]["name"], listed[1]["name"], listed[1]["active"]), ("Work", "DEFAULT 2", True))
        self.assertIn("* 2  DEFAULT 2", self.run_z20("profile"))


if __name__ == "__main__":
    unittest.main()
