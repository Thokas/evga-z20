.pragma library
/*
 * Lighting presets: a name, an effect and its settings, turned into z20
 * commands. A preset: { name, effect, colors (rrggbb, as many as the effect
 * takes), brightness (%), cycle (ms), direction, zone, onKey, stop, mode,
 * fadeOut, keys }. The keyboard's own effects become `z20 light`, with what
 * Unleash sets for them as well: zone, the keys the effect runs on ("all", or
 * a comma list of ZONES); onKey, it starts on the first key press (dark until
 * then, also after plugging in or a welcome effect); stop, what stops it
 * (STOPS); reactive's mode (REACTIVE_MODES) and fadeOut (0-100, as Unleash's
 * slider: 0 the longest glow); the software ones (z20 works out the colors
 * and sends them 25 times a second) become `z20 animate`. keys: colors of
 * single keys over the effect, { LED name (as z20 leds names it): rrggbb },
 * 000000 dark; `z20 color`, the other keys showing the effect.
 */

// Effects in the order the editor offers them, with how many colors each takes.
var EFFECTS = ["off", "static", "breathing", "wave", "spiral", "pulse", "stars", "reactive", "rows", "fade",
               "explosion", "raining", "barber", "lightbar", "thunder",
               "aurora", "fire", "rain", "ripple", "scanner", "gradient"];
// The presence sensor's effects, which the keyboard also runs as the lighting (as Unleash offers them):
// their colors, direction and brightness are the welcome effect's too (z20 sensor welcome).
var SENSOR_EFFECTS = ["explosion", "raining", "barber", "lightbar", "thunder"];
var SOFTWARE = ["aurora", "fire", "rain", "ripple", "scanner", "gradient"];
var LABELS = { off: "Off", static: "Static", breathing: "Breathing", wave: "Wave", spiral: "Spiral", pulse: "Pulse",
               stars: "Stars", reactive: "Reactive (on key press)", rows: "Rows", fade: "Fade",
               explosion: "Explosion", raining: "Raining", barber: "Barber pole", lightbar: "Light bar wave",
               thunder: "Thunder",
               aurora: "Aurora (software)", fire: "Fire (software)", rain: "Rain (software)",
               ripple: "Ripples (software)", scanner: "Scanner (software)", gradient: "Gradient (software)" };
var COLOR_SLOTS = { off: 0, static: 1, breathing: 2, wave: 8, spiral: 8, pulse: 8, stars: 0, reactive: 8, rows: 7,
                    fade: 1, explosion: 7, raining: 0, barber: 3, lightbar: 1, thunder: 1,
                    aurora: 8, fire: 8, rain: 2, ripple: 8, scanner: 1, gradient: 8 };
// Effects with a cycle time (their speed) and with a direction.
var HAS_CYCLE = ["breathing", "wave", "spiral", "pulse", "stars", "reactive", "aurora", "fire", "rain", "ripple",
                 "scanner"];
var DIRECTIONS = { wave: ["right", "left", "up", "down"], spiral: ["cw", "ccw"], explosion: ["out", "in"],
                   barber: ["left", "right"] };
// What every keyboard effect has, as z20 light's --zone, --stop, and reactive's --mode, with the factory's first.
var ZONES = ["numpad", "fkeys", "numbers", "arrows", "wasd", "bars"];  // as z20 lists them
var STOPS = ["never", "press", "release"];
var REACTIVE_MODES = ["typed", "one-key", "3x3"];
var FADE_OUT = 50;  // the factory's

// Fade-out as the keyboard stores it (z20's fade_out_raw): two slider values may be one stored value.
function fadeOutRaw(s) {
    return s <= 50 ? 82 - s : Math.floor((100 - s) / 1.56);
}

var RAINBOW = ["ff0000", "ff8000", "ffff00", "00ff00", "00ffff", "0000ff", "ff00ff"];

function isSoftware(effect) {
    return SOFTWARE.indexOf(effect) >= 0;
}

// What the widget starts with; everything here can be changed in its settings.
function defaults() {
    return [
        { name: "Rainbow", effect: "wave", colors: RAINBOW, brightness: 100, cycle: 3000, direction: "right" },
        { name: "Ocean", effect: "wave", colors: ["0010ff", "0060ff", "00c0ff", "00ffd0"], brightness: 100,
          cycle: 6000, direction: "left" },
        { name: "Sunset", effect: "wave", colors: ["ff2000", "ff6000", "ffa000", "ff0040"], brightness: 100,
          cycle: 5000, direction: "right" },
        { name: "Breathing blue", effect: "breathing", colors: ["0040ff", "000000"], brightness: 100, cycle: 4000 },
        { name: "Spiral", effect: "spiral", colors: RAINBOW, brightness: 100, cycle: 3000, direction: "cw" },
        { name: "Stars", effect: "stars", colors: [], brightness: 100, cycle: 2000 },
        { name: "Typing", effect: "reactive", colors: ["00e0ff"], brightness: 100, cycle: 300 },
        { name: "Aurora", effect: "aurora", colors: ["00ff90", "00a0ff", "6020ff"], brightness: 100, cycle: 10000 },
        { name: "Fire", effect: "fire", colors: ["ff0000", "ff6000", "ffc000"], brightness: 100, cycle: 800 },
        { name: "Matrix", effect: "rain", colors: ["00ff40", "c0ffc0"], brightness: 100, cycle: 1500 },
        { name: "Ripples", effect: "ripple", colors: ["00c0ff", "ff00c0", "ffc000"], brightness: 100, cycle: 2500 },
        { name: "White", effect: "static", colors: ["ffffff"], brightness: 60 },
        { name: "Gaming", effect: "static", colors: ["180030"], brightness: 100,
          keys: { W: "ff3000", A: "ff3000", S: "ff3000", D: "ff3000", Up: "00b0ff", Down: "00b0ff",
                  Left: "00b0ff", Right: "00b0ff", Esc: "ff0000" } },
        { name: "Off", effect: "off", colors: [] }
    ];
}

// The z20 commands (argument lists) for a preset; live: only for now (`--live`),
// else stored in the profile, or saved as the effect the z20-animate service runs.
function commands(preset, live) {
    var effect = preset.effect;
    var a = [isSoftware(effect) ? "animate" : "light", effect]
        .concat((preset.colors || []).slice(0, COLOR_SLOTS[effect] || 0));
    if (effect !== "off" && preset.brightness !== undefined) {
        a.push("--brightness", String(Math.round(preset.brightness)));
    }
    if (HAS_CYCLE.indexOf(effect) >= 0 && preset.cycle) {
        a.push("--cycle", String(Math.round(preset.cycle)));
    }
    if (DIRECTIONS[effect] && preset.direction) {
        a.push("--direction", preset.direction);
    }
    if (!isSoftware(effect) && effect !== "off") {  // said either way: a preset is the whole effect
        a.push("--zone", preset.zone || "all", "--stop", preset.stop || "never");
        if (effect === "reactive") {
            a.push("--mode", preset.mode || "typed",
                   "--fade-out", String(preset.fadeOut !== undefined ? Math.round(preset.fadeOut) : FADE_OUT));
        }
        a.push(preset.onKey ? "--on-key" : "--no-on-key");
    }
    if (isSoftware(effect)) {
        a.push(live ? "--live" : "--save");
        return [a, keyColors(preset.keys, live)];
    }
    if (live) {
        a.push("--live");
    }
    // A software effect would cover the keyboard's own: stop it (--live: for now).
    return [["animate", "off"].concat(live ? ["--live"] : []), a, keyColors(preset.keys, live)];
}

// The keys' own colors as one z20 color: those of keys, the others none (the effect shows there), so
// a preset without any takes away the last one's.
function keyColors(keys, live) {
    var byColor = {};
    Object.keys(keys || {}).forEach(function (name) {
        (byColor[keys[name]] = byColor[keys[name]] || []).push(name);
    });
    var a = ["color", "all", "none"];
    Object.keys(byColor).forEach(function (color) {
        a.push(byColor[color].join(","), color);
    });
    return live ? a.concat(["--live"]) : a;
}

// Back to what is stored: the saved software effect (or none), the profile's lighting and the keys' colors.
var RESTORE = [["animate", "reload"], ["light", "reload"], ["color", "reload"]];

// A preset as presence.ini's "away light", which the presence service shows while you are away:
// its z20 light or animate arguments without --live, as z20 presence settings prints them (without
// the keys' colors, without waiting for a key: nobody types while away, and without what is as from
// the factory, so it reads as before these were there).
function awayLight(preset) {
    var lighting = commands(preset, true).filter(function (a) {
        return a[0] === "light" || a[0] === "animate" && a[1] !== "off";
    })[0];
    var plain = { "--zone": "all", "--stop": "never", "--mode": "typed", "--fade-out": String(FADE_OUT) };
    var out = [];
    for (var i = 0; i < lighting.length; i++) {
        if (plain[lighting[i]] !== undefined && lighting[i + 1] === plain[lighting[i]]) {
            i++;
        } else if (["--live", "--on-key", "--no-on-key"].indexOf(lighting[i]) < 0) {
            out.push(lighting[i]);
        }
    }
    return out.join(" ");
}

// The colors as the keyboard keeps them after z20 light: breathing with one goes out to dark, the animated
// effects repeat theirs to fill every slot (z20's fill_colors).
function filled(effect, colors) {
    var count = COLOR_SLOTS[effect] || 0;
    if (effect === "breathing" && colors.length === 1) {
        return colors.concat(["000000"]);
    }
    if (count > 2 && colors.length > 0 && colors.length < count) {
        var out = [];
        while (out.length < count) {
            out = out.concat(colors);
        }
        return out.slice(0, count);
    }
    return colors;
}

function hex(color) {
    return String(color).replace(/^#/, "").toLowerCase();
}

// Whether the preset is the lighting the keyboard has stored, what a reload brings back: stored, a status of
// z20 from 2026-11-16 on (z20 status --json: lighting, saved_animation, key_colors). Its effect, colors, speed,
// brightness, direction, zone, start and stop, reactive's mode and fade-out (z20 from 2026-11-19 on) and keys'
// colors, where the preset has them (a preset without colors keeps the
// profile's, so any count).
function matches(preset, stored) {
    if (!preset || !stored || !stored.lighting) {
        return false;
    }
    var same = function (a, b) {
        return a.length === b.length && a.every(function (c, i) { return hex(c) === hex(b[i]); });
    };
    var own = preset.keys || {}, keys = stored.key_colors || {};
    if (Object.keys(own).length !== Object.keys(keys).length
            || Object.keys(own).some(function (k) { return hex(own[k]) !== hex(keys[k] || ""); })) {
        return false;
    }
    var colors = (preset.colors || []).slice(0, COLOR_SLOTS[preset.effect] || 0);
    var anim = stored.saved_animation;
    if (isSoftware(preset.effect)) {
        return !!anim && anim.effect === preset.effect && (!colors.length || same(colors, anim.colors))
            && (preset.brightness === undefined || Math.abs((anim.brightness === null ? 100 : anim.brightness)
                                                            - preset.brightness) <= 1)
            && (!preset.cycle || anim.cycle_ms === Math.round(preset.cycle));
    }
    var l = stored.lighting;
    return !anim && l.effect === preset.effect  // a software effect stored would cover it
        && (!colors.length || !l.colors || same(filled(preset.effect, colors), l.colors))
        && (preset.effect === "off" || preset.brightness === undefined || l.brightness === undefined
            || Math.abs(l.brightness - preset.brightness) <= 1)  // percent → 0-255 → percent may move by one
        && (HAS_CYCLE.indexOf(preset.effect) < 0 || !preset.cycle || l.cycle_ms === undefined
            || l.cycle_ms === Math.round(preset.cycle))
        && (!DIRECTIONS[preset.effect] || !preset.direction || !l.direction || l.direction === preset.direction)
        && (l.on_key === undefined || !!preset.onKey === l.on_key)
        && (l.zone === undefined || (preset.zone || "all") === l.zone.join(","))
        && (l.stop === undefined || (preset.stop || "never") === l.stop)
        && (l.mode === undefined || (preset.mode || "typed") === l.mode)
        && (l.fade_out === undefined
            || fadeOutRaw(preset.fadeOut !== undefined ? preset.fadeOut : FADE_OUT) === fadeOutRaw(l.fade_out));
}

// The lighting the keyboard has stored (as for matches()) as a preset named name: the software effect where
// one is stored, else the profile's own effect with all it has; the keys' own colors. null for an effect a
// preset can't have.
function fromKeyboard(stored, name) {
    var anim = stored.saved_animation, l = stored.lighting || {};
    var p = anim ? { name: name, effect: anim.effect, colors: (anim.colors || []).map(hex),
                     brightness: anim.brightness === null ? 100 : anim.brightness, cycle: anim.cycle_ms }
                 : { name: name, effect: l.effect, colors: (l.colors || []).map(hex), brightness: l.brightness,
                     cycle: l.cycle_ms, direction: l.direction, onKey: l.on_key || undefined,
                     zone: l.zone && l.zone.join(",") !== "all" ? l.zone.join(",") : undefined,
                     stop: l.stop && l.stop !== "never" ? l.stop : undefined,
                     mode: l.mode && l.mode !== "typed" ? l.mode : undefined,
                     fadeOut: l.fade_out !== undefined && l.fade_out !== FADE_OUT ? l.fade_out : undefined };
    if (EFFECTS.indexOf(p.effect) < 0) {
        return null;
    }
    Object.keys(p).forEach(function (k) {
        if (p[k] === undefined || p[k] === null) {
            delete p[k];
        }
    });
    var keys = stored.key_colors || {};
    if (Object.keys(keys).length) {
        p.keys = {};
        Object.keys(keys).forEach(function (k) { p.keys[k] = hex(keys[k]); });
    }
    return p;
}

// The stored list, or the defaults when there is none yet.
function parse(text) {
    try {
        var list = JSON.parse(text);
        return Array.isArray(list) && list.length ? list : defaults();
    } catch (e) {
        return defaults();
    }
}
