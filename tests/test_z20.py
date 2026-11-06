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

    def test_general_reads_and_the_three_writes(self):
        for command in (0x01, 0x06, 0x07, 0x0B, 0x0F):
            z20.check_request(report(4, 0xEA, 0x02, command, z20.READ))
        for command in (0x06, 0x08, 0x0B):
            z20.check_request(report(4, 0xEA, 0x02, command, z20.WRITE))
        z20.check_request(report(4, 0xEA, 0x02, 0x07, z20.WRITE, 1, 0, 45, 0, 0, 0x6B, 0))  # Fn+Q in RAM
        for layer, pos in ((2, 45), (0, 108), (0, 121), (0, 17)):  # no layer 2, not Fn, no such keys
            with self.assertRaises(z20.Z20Error):
                z20.check_request(report(4, 0xEA, 0x02, 0x07, z20.WRITE, layer, 0, pos))
        with self.assertRaises(z20.Z20Error):
            z20.check_request(report(4, 0xEA, 0x02, 0x0F, z20.WRITE))  # 6KRO/NKRO: read only
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
            r = bytearray(request).ljust(17, b"\0")
            z20.check_request(r)
            if r[3] == 0x12:
                self.sent.append(("save",))
            elif r[4] == z20.WRITE:
                self.keys[r[5], r[7]] = bytes(r[8:12])
                self.sent.append(("key", r[5], r[7]))
            return bytes(8) + self.keys.get((r[5], r[7]), bytes(4))

    def test_parts_go_to_ram(self):
        old = profile(1)
        new = z20.set_lighting(old, "static", [b"\x00\x00\xff"], None, None)
        new[z20.P_FN_KEYS + 45 * 4:z20.P_FN_KEYS + 46 * 4] = b"\x00\x00\x6b\x00"
        kb = self.Keyboard()
        self.assertTrue(kb.update_ram(old, new))
        self.assertEqual(kb.sent, [("ram", 0x0C, b"\x01\x00"), ("ram", 0x0D, bytes(new[z20.P_STATIC:z20.P_STATIC + 2])),
                                   ("key", 1, 45)])

    def test_other_changes_need_a_reload(self):
        old = profile(1)
        renamed = bytearray(old)
        renamed[10] ^= 1  # the name
        for new in (renamed, z20.set_sensor(old, ["leave", "lock"])):  # the sensor: never through RAM
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


class PresenceService(unittest.TestCase):
    def test_leave_and_come_after_their_times(self):
        p = z20.Presence(leave_after=30, come_after=1)
        events = [(t, p.update(near, t)) for t, near in ((0, True), (5, False), (20, True), (21, False),
                                                        (50, False), (51, False), (60, True), (60.5, True),
                                                        (61, True), (62, True))]
        # away 5-20 is too short; away from 21 counts after 30 s; near from 60 counts after 1 s
        self.assertEqual([(t, e) for t, e in events if e], [(51, "leave"), (61, "come")])

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
        self.assertEqual(z20.lighting(q), {"effect": "static", "colors": ["#123456"]})

    def test_breathing_keeps_the_hold_percentages(self):
        p = profile()
        q = z20.set_lighting(p, "breathing", [b"\x00\xff\x00", b"\x00\x00\x00"], None, 4000)
        self.assertEqual(changed(p, q) - {1288, 1289, 1356, 1357, 1360, 1361, 1362, 1365, 1366, 1367}, set())
        self.assertEqual(z20.lighting(q), {"effect": "breathing", "colors": ["#00ff00", "#000000"], "cycle_ms": 4000})

    def test_effects_keep_their_stored_colors(self):
        p = profile()
        q = z20.set_lighting(p, "wave", [], None, None)
        self.assertEqual(changed(p, q) - {1288, 1289}, set())
        self.assertEqual((q[1288], q[1289]), (5, p[z20.P_WAVE + 4]))  # the wave's own direction

    def test_off(self):
        q = z20.set_lighting(profile(), "off", [], None, None)
        self.assertEqual(z20.lighting(q), {"effect": "off"})


if __name__ == "__main__":
    unittest.main()
