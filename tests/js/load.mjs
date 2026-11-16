// The settings app's JavaScript (app/qml/lib) in node: without its QML pragmas, with what it imports
// (.import, given as deps) and a stand-in for what the page's QML context gives it (i18n, as written
// with %1, %2, ... filled in).
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const lib = path.join(here, "../../app/qml/lib");

export function i18n(text, ...args) {
    return args.reduce((t, a, i) => t.replaceAll(`%${i + 1}`, String(a)), text);
}

export function load(file, names, deps = {}) {
    const src = fs.readFileSync(path.join(lib, file), "utf8").split("\n")
        .filter(l => !l.startsWith(".pragma") && !l.startsWith(".import")).join("\n");
    return new Function(...Object.keys(deps), "i18n", `${src}\nreturn { ${names.join(", ")} };`)(
        ...Object.values(deps), i18n);
}

// The keyboard as z20 leds has it (ISO or ANSI), from this checkout's z20: no keyboard needed.
export function leds(layout = "iso") {
    const z20 = path.join(here, "../../z20");
    return JSON.parse(execFileSync("python3", ["-I", z20, "leds", layout, "--json"], { encoding: "utf8" })).leds;
}

export const Presets = load("presets.js", ["EFFECTS", "SOFTWARE", "LABELS", "COLOR_SLOTS", "HAS_CYCLE", "DIRECTIONS",
                                           "RAINBOW", "isSoftware", "defaults", "commands", "keyColors", "RESTORE",
                                           "awayLight", "filled", "matches", "fromKeyboard", "parse"]);
