// keyboard.js: the keys' labels and the groups the Lighting page offers.
import { test } from "node:test";
import assert from "node:assert/strict";
import { load, leds } from "./load.mjs";

const K = load("keyboard.js", ["label", "groups", "LABELS"]);
const iso = leds("iso"), ansi = leds("ansi");
const named = (list, name) => list.find(l => l.name === name);

test("labels: short names, the numpad's digits, nothing on the light bars and logo", () => {
    assert.equal(K.label(named(iso, "KP7")), "7");
    assert.equal(K.label(named(iso, "PrintScreen")), "PrtSc");
    assert.equal(K.label(named(iso, "Space")), "");
    assert.equal(K.label(named(iso, "W")), "W");
    assert.equal(K.label(named(iso, "LeftBar1")), "");
    assert.equal(K.label(named(iso, "Logo1")), "");
});

test("groups take only the LEDs there are", () => {
    const g = list => Object.fromEntries(K.groups(list).map(x => [x.name, x.names]));
    const isoGroups = g(iso), ansiGroups = g(ansi);
    assert.deepEqual(isoGroups.WASD, ["W", "A", "S", "D"]);
    assert.equal(isoGroups.Letters.length, 26);
    assert.equal(isoGroups["F1–F12"].length, 12);
    assert.equal(isoGroups["Light bars"].length, 18);
    assert.equal(isoGroups.Logo.length, 4);
    assert.ok(isoGroups.Numpad.includes("NumLock") && isoGroups.Numpad.includes("KPEnter"));
    assert.equal(isoGroups.Everything.length, iso.length);
    assert.ok(isoGroups["All keys"].includes("ISO\\") && !ansiGroups["All keys"].includes("ISO\\"));
    assert.equal(ansiGroups.Everything.length, ansi.length);
});
