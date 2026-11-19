// presets.js: the presets as z20 commands, and as the keyboard stores them.
import { test } from "node:test";
import assert from "node:assert/strict";
import { Presets as P } from "./load.mjs";

const byName = name => P.defaults().find(p => p.name === name);
// What z20 status --json says the keyboard has stored after a preset was applied.
function stored(preset, extra = {}) {
    const software = P.isSoftware(preset.effect);
    const colors = (preset.colors || []).slice(0, P.COLOR_SLOTS[preset.effect] || 0);
    return {
        lighting: software ? { effect: "wave", colors: [], brightness: 100 } : {
            effect: preset.effect, colors: P.filled(preset.effect, colors).map(c => "#" + c),
            brightness: preset.brightness, cycle_ms: preset.cycle, direction: preset.direction,
            ...(preset.effect === "off" ? {} : { on_key: !!preset.onKey, zone: (preset.zone || "all").split(","),
                                                 stop: preset.stop || "never" }),
            ...(preset.effect === "reactive" ? { mode: preset.mode || "typed", fade_out: preset.fadeOut ?? 50 } : {}) },
        saved_animation: software ? { effect: preset.effect, colors, cycle_ms: preset.cycle,
                                      brightness: preset.brightness } : null,
        key_colors: preset.keys || {},
        ...extra,
    };
}

test("the built-in presets are whole", () => {
    const list = P.defaults();
    assert.equal(new Set(list.map(p => p.name)).size, list.length, "names are unique");
    for (const p of list) {
        assert.ok(P.EFFECTS.includes(p.effect), p.name);
        assert.ok((p.colors || []).length <= (P.COLOR_SLOTS[p.effect] || 0), p.name);
        assert.ok(P.LABELS[p.effect], p.name);
    }
});

test("a keyboard effect stops the software one, then lights, then sets the keys' colors", () => {
    const gaming = byName("Gaming");
    assert.deepEqual(P.commands(gaming, true), [
        ["animate", "off", "--live"],
        ["light", "static", "180030", "--brightness", "100", "--zone", "all", "--stop", "never", "--no-on-key",
         "--live"],
        ["color", "all", "none", "W,A,S,D", "ff3000", "Up,Down,Left,Right", "00b0ff", "Esc", "ff0000", "--live"],
    ]);
    assert.deepEqual(P.commands(gaming, false)[0], ["animate", "off"]);
});

test("a software effect runs as the service: saved, or for now", () => {
    const fire = byName("Fire");
    assert.deepEqual(P.commands(fire, false), [
        ["animate", "fire", "ff0000", "ff6000", "ffc000", "--brightness", "100", "--cycle", "800", "--save"],
        ["color", "all", "none"],
    ]);
    assert.equal(P.commands(fire, true)[0].at(-1), "--live");
});

test("only the settings an effect has go out", () => {
    const [, light] = P.commands({ name: "x", effect: "static", colors: ["111111", "222222"], cycle: 900,
                                   direction: "left", brightness: 40 }, false);
    assert.deepEqual(light, ["light", "static", "111111", "--brightness", "40", "--zone", "all", "--stop", "never",
                             "--no-on-key"]);
    const [, off] = P.commands({ name: "x", effect: "off", colors: [], brightness: 40 }, false);
    assert.deepEqual(off, ["light", "off"]);
});

test("a preset starts on a key press or as the profile loads, said either way", () => {
    const wave = { ...byName("Rainbow"), onKey: true };
    assert.equal(P.commands(wave, false)[1].at(-1), "--on-key");
    assert.equal(P.commands(wave, true)[1].at(-2), "--on-key");
    assert.ok(P.matches(wave, stored(wave)));
    assert.ok(!P.matches(byName("Rainbow"), stored(wave)), "the keyboard waits for a key, the preset doesn't");
    assert.ok(P.matches(byName("Rainbow"), { ...stored(byName("Rainbow")), lighting: {
        ...stored(byName("Rainbow")).lighting, on_key: undefined } }), "a z20 from before 2026-11-19");
    assert.equal(P.awayLight(wave), P.awayLight(byName("Rainbow")), "away, nobody presses a key");
    assert.equal(P.fromKeyboard(stored(wave), "x").onKey, true);
    assert.equal(P.fromKeyboard(stored(byName("Rainbow")), "x").onKey, undefined);
});

test("zone, stop, and reactive's mode and fade-out: said either way, compared, kept from the keyboard", () => {
    const typing = { ...byName("Typing"), zone: "arrows,wasd", stop: "release", mode: "3x3", fadeOut: 20 };
    assert.deepEqual(P.commands(typing, false)[1].slice(-9), ["--zone", "arrows,wasd", "--stop", "release", "--mode",
                                                             "3x3", "--fade-out", "20", "--no-on-key"]);
    assert.deepEqual(P.commands(byName("Typing"), false)[1].slice(-9), ["--zone", "all", "--stop", "never", "--mode",
                                                                        "typed", "--fade-out", "50", "--no-on-key"]);
    assert.ok(P.matches(typing, stored(typing)));
    assert.ok(!P.matches(byName("Typing"), stored(typing)));
    assert.ok(P.matches({ ...typing, fadeOut: 52 }, stored({ ...typing, fadeOut: 53 })), "the same stored value");
    assert.equal(P.awayLight(byName("Typing")), P.awayLight({ ...byName("Typing"), mode: "typed", fadeOut: 50 }));
    assert.match(P.awayLight(typing), /--zone arrows,wasd --stop release --mode 3x3 --fade-out 20$/);
    const own = P.fromKeyboard(stored(typing), "x");
    assert.deepEqual([own.zone, own.stop, own.mode, own.fadeOut], ["arrows,wasd", "release", "3x3", 20]);
    const plain = P.fromKeyboard(stored(byName("Typing")), "x");
    assert.deepEqual([plain.zone, plain.stop, plain.mode, plain.fadeOut], [undefined, undefined, undefined, undefined]);
});

test("the away light is the lighting alone, without --live", () => {
    assert.equal(P.awayLight(byName("Gaming")), "light static 180030 --brightness 100");
    assert.equal(P.awayLight(byName("Fire")), "animate fire ff0000 ff6000 ffc000 --brightness 100 --cycle 800");
    assert.equal(P.awayLight({ name: "Off", effect: "off", colors: [] }), "light off");
});

test("colors filled as the keyboard keeps them", () => {
    assert.deepEqual(P.filled("breathing", ["00ff00"]), ["00ff00", "000000"]);
    assert.deepEqual(P.filled("wave", ["a", "b", "c"]), ["a", "b", "c", "a", "b", "c", "a", "b"]);
    assert.deepEqual(P.filled("rows", ["a", "b"]), ["a", "b", "a", "b", "a", "b", "a"]);
    assert.deepEqual(P.filled("static", ["a"]), ["a"]);
});

test("every built-in preset is recognised as stored, and only it", () => {
    for (const p of P.defaults()) {
        if (p.effect === "off" || !p.colors.length && p.effect !== "stars") {
            continue;
        }
        const found = P.defaults().filter(q => P.matches(q, stored(p))).map(q => q.name);
        assert.ok(found.includes(p.name), `${p.name}: ${found}`);
    }
    assert.deepEqual(P.defaults().filter(q => P.matches(q, stored(byName("Rainbow")))).map(q => q.name), ["Rainbow"]);
});

test("what differs is no match: brightness by more than one, direction, keys, a software effect over it", () => {
    const rainbow = byName("Rainbow");
    assert.ok(P.matches(rainbow, stored({ ...rainbow, brightness: 99 })), "rounding moves it by one");
    assert.ok(!P.matches(rainbow, stored({ ...rainbow, brightness: 97 })));
    assert.ok(!P.matches(rainbow, stored({ ...rainbow, direction: "left" })));
    assert.ok(!P.matches(rainbow, stored(rainbow, { key_colors: { W: "ff0000" } })));
    assert.ok(!P.matches(byName("Gaming"), stored(byName("Gaming"), { key_colors: {} })));
    assert.ok(!P.matches(rainbow, stored(rainbow, { saved_animation: { effect: "fire", colors: [] } })));
    assert.ok(!P.matches(rainbow, null) && !P.matches(null, stored(rainbow)));
});

test("the keyboard's lighting as a preset, which it then is", () => {
    const keyboard = {
        lighting: { effect: "wave", colors: ["#ff0000", "#d80c36", "#000000", "#ff0000", "#d82537", "#000000",
                                             "#d8122c", "#ffffff"], direction: "right", cycle_ms: 3000, brightness: 100 },
        saved_animation: null, key_colors: { Esc: "FF0000" },
    };
    const own = P.fromKeyboard(keyboard, "Profile 1");
    assert.deepEqual(own, { name: "Profile 1", effect: "wave", colors: ["ff0000", "d80c36", "000000", "ff0000",
                            "d82537", "000000", "d8122c", "ffffff"], brightness: 100, cycle: 3000, direction: "right",
                            keys: { Esc: "ff0000" } });
    assert.ok(P.matches(own, keyboard));
    assert.deepEqual(P.defaults().filter(q => P.matches(q, keyboard)), []);
    const anim = P.fromKeyboard({ lighting: { effect: "static" }, saved_animation: { effect: "gradient",
                                  colors: ["ff0080"], cycle_ms: null, brightness: null }, key_colors: {} }, "x");
    assert.deepEqual(anim, { name: "x", effect: "gradient", colors: ["ff0080"], brightness: 100 });
    assert.equal(P.fromKeyboard({ lighting: { effect: "recorded" }, saved_animation: null }, "x"), null);
    assert.equal(P.fromKeyboard({ lighting: { effect: "thunder", colors: ["#0000ff"] }, saved_animation: null }, "x")
        .effect, "thunder", "the presence sensor's effects are lighting too");
});

test("the stored list, else the defaults", () => {
    assert.equal(P.parse("").length, P.defaults().length);
    assert.equal(P.parse("not json").length, P.defaults().length);
    assert.equal(P.parse("[]").length, P.defaults().length);
    assert.deepEqual(P.parse('[{"name":"a","effect":"off"}]'), [{ name: "a", effect: "off" }]);
});
