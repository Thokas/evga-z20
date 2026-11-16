// preview.js: every effect drawn over the keyboard as z20 leds has it.
import { test } from "node:test";
import assert from "node:assert/strict";
import { load, leds, Presets } from "./load.mjs";

const V = load("preview.js", ["renderer", "hex", "blend", "SOFTWARE"], { Presets });
const iso = leds("iso");

test("every effect gives a color for each LED, frame after frame", () => {
    for (const effect of Presets.EFFECTS) {
        const preset = Presets.defaults().find(p => p.effect === effect)
            || { effect, colors: ["ff0000", "00ff00"], cycle: 1500, brightness: 80, direction: "up" };
        const r = V.renderer(preset, iso);
        let lit = 0;
        for (let i = 0; i < 150; i++) {
            const frame = r.at(i * 0.04);
            assert.equal(frame.length, iso.length, effect);
            for (const c of frame) {
                assert.ok(c.length === 3 && c.every(v => Number.isFinite(v) && v >= -0.5 && v <= 255.5), `${effect}: ${c}`);
                lit += Math.max(...c) > 8;
            }
        }
        assert.ok(effect === "off" ? lit === 0 : lit > 0, `${effect} lights something`);
    }
});

test("still effects are drawn once", () => {
    const still = e => V.renderer({ effect: e, colors: ["ff0000"] }, iso).still;
    assert.ok(still("off") && still("static") && still("rows"));
    assert.ok(!still("wave") && !still("fire") && !still("breathing"));
    assert.ok(V.renderer({ effect: "gradient", colors: ["ff0000", "0000ff"] }, iso).still, "a gradient without a cycle");
    assert.ok(!V.renderer({ effect: "gradient", colors: ["ff0000", "0000ff"], cycle: 4000 }, iso).still);
});

test("brightness scales the colors; 0 is dark", () => {
    const at = b => V.renderer({ effect: "static", colors: ["ff8000"], brightness: b }, iso).at(0)[0];
    assert.deepEqual(at(100), [255, 128, 0]);
    assert.deepEqual(at(50).map(Math.round), [128, 64, 0]);
    assert.deepEqual(at(0), [0, 0, 0]);
});

test("a wave runs the way it is set", () => {
    // A quarter cycle later, a key a quarter of the keyboard to the right has the color the first one had.
    const xs = iso.map(l => l.x), x0 = Math.min(...xs), width = Math.max(...xs) - x0;
    const nearest = x => iso.reduce((a, l) => Math.abs(l.x - x) < Math.abs(a.x - x) ? l : a);
    const a = nearest(x0 + 0.2 * width), b = nearest(a.x + 0.25 * width);
    const color = (direction, led, t) =>
        V.renderer({ effect: "wave", colors: ["ff0000", "0000ff"], cycle: 1000, direction }, iso).at(t)[iso.indexOf(led)];
    const close = (c, d) => c.every((v, i) => Math.abs(v - d[i]) < 40);
    assert.ok(close(color("right", b, 0.25), color("right", a, 0)), "right: it arrives on the right");
    assert.ok(!close(color("left", b, 0.25), color("left", a, 0)), "left: it doesn't");
});

test("colors as #rrggbb, clamped", () => {
    assert.equal(V.hex([255, 128, 0]), "#ff8000");
    assert.equal(V.hex([300, -5, 15.6]), "#ff0010");
    assert.deepEqual(V.blend([[0, 0, 0], [255, 255, 255]], 0.5, false), [127.5, 127.5, 127.5]);
    assert.deepEqual(V.blend([[255, 0, 0], [0, 0, 255]], 1, true), [255, 0, 0]);
});
