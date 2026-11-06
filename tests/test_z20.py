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

    def test_macros_are_only_read(self):
        z20.check_request(report(9, 0xEA, 0x02, z20.READ, 0, 0, z20.FAIL))
        z20.check_request(report(10, 0xEA, 0x02, z20.READ, 3, 0, z20.FAIL))
        with self.assertRaises(z20.Z20Error):
            z20.check_request(report(9, 0xEA, 0x02, z20.WRITE, 3, 0, z20.FAIL))


class Reports(unittest.TestCase):
    def test_checksum_makes_the_sum_zero(self):
        p = profile()
        self.assertEqual((sum(p[8:]) + p[7]) & 0xFF, 0)

    def test_macro_actions(self):
        data = bytes([0x01, 39, 0, 0x1A, 0x9A, 0x7A, 0xFA, 0x03, 0xE9, 0x00, 0x03, 0, 0,
                      0x70, 0xF0, 0x78, 0xF8, 0x80, 0x10, 0x00, 0x20, 0x00])
        self.assertEqual(z20.macro_actions(data), [
            "wait 20 ms", "W down", "W up", "left button down", "left button up", "VolumeUp down",
            "media up", "LCtrl down", "LCtrl up", "wheel down", "wheel up", "mouse to 16,32"])

    def test_key_functions(self):
        names = {1: "Autorunner"}
        self.assertEqual(z20.key_function(bytes([3, 1, 8, 0]), names)[0],
                         'macro 1 "Autorunner" (loop until pressed again)')
        self.assertEqual(z20.key_function(bytes([0, 0x05, 0x1A, 0]), names)[0], "key LCtrl+LAlt+W")
        self.assertEqual(z20.key_function(bytes([2, 0xCD, 0, 0]), names)[0], "media PlayPause")
        self.assertEqual(z20.key_function(bytes([7, 0, 0, 0]), names)[0], "left click")
        self.assertEqual(z20.key_function(bytes([0xFF] * 4), names)[0], "disabled")

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
