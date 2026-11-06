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
        for rid, size in ((5, 521), (6, 792), (7, 136), (11, 2056), (15, 264)):  # 5 is the firmware update
            with self.assertRaises(z20.Z20Error):
                z20.check_request(report(rid, 0xEA, 0x02, z20.READ, size=size))

    def test_general_reads_and_the_three_writes(self):
        for command in (0x01, 0x06, 0x07, 0x0B, 0x0F):
            z20.check_request(report(4, 0xEA, 0x02, command, z20.READ))
        for command in (0x06, 0x08, 0x0B):
            z20.check_request(report(4, 0xEA, 0x02, command, z20.WRITE))
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
