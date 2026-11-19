/*
 * The app's "Lighting" page: the lighting presets (the widget's popup offers
 * them too). On the left the presets in their order, to pick one, add,
 * remove and move them. On the right the one picked: on a drawing of the
 * keyboard as it runs (KeyboardView), its effect (the keyboard's own, or one
 * z20 animates: colors, brightness, speed, direction) and, beside it, keys
 * with colors of their own over the effect: select them on the drawing (or a
 * group: WASD, arrows, ...), then a color, dark, or the effect again. Above
 * the drawing: try it on the keyboard (only for now: what is stored comes
 * back with "Back to stored"), or have every change shown there as it's
 * made, or apply it (stored, as the widget's popup applies one). The one
 * that is the lighting the keyboard has stored, however it got there, is
 * marked, and the page opens on it.
 * Saved a moment after each change (~/.config/z20/presets.json).
 */

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

import "lib" as Lib
import "lib/keyboard.js" as Keyboard
import "lib/presets.js" as Presets

Kirigami.Page {
    id: page

    property var presets: []
    property int current: 0
    readonly property var preset: presets[current] || null
    readonly property int slots: preset ? Presets.COLOR_SLOTS[preset.effect] || 0 : 0
    // The one that is the lighting the keyboard has stored, whoever applied it (-1: none).
    readonly property int appliedIndex: z20.appliedIndex(presets)
    // The keys' own colors, most keys first: [{color, names}].
    readonly property var keyColors: {
        const keys = preset && preset.keys || {};
        const byColor = {};
        Object.keys(keys).forEach(name => (byColor[keys[name]] = byColor[keys[name]] || []).push(name));
        return Object.keys(byColor).map(color => ({ color: color, names: byColor[color] }))
            .sort((a, b) => b.names.length - a.names.length);
    }

    Component.onCompleted: {
        z20.refreshLeds();
        z20.refresh();  // what shows, to find the preset applied
    }

    // The presets once read (the defaults while there are none stored), anew when they are first stored (the
    // first start puts the keyboard's lighting first) unless changed here already; then the one applied is
    // picked, once the keyboard's state is read too.
    property bool chosen: false
    property bool edited: false
    Connections {
        target: z20
        function onDetailsReadChanged() {
            if (z20.detailsRead && !page.presets.length) {
                page.presets = Presets.parse(z20.presetsText);
            }
            page.chooseApplied();
        }
        function onPresetsTextChanged() {
            if (!page.edited && z20.presetsText) {
                page.presets = Presets.parse(z20.presetsText);
                page.chosen = false;
                page.chooseApplied();
            }
        }
        function onStatusChanged() {
            page.chooseApplied();
        }
    }

    function chooseApplied() {
        if (!chosen && presets.length && z20.status) {
            chosen = true;
            if (appliedIndex >= 0) {
                current = appliedIndex;
            }
        }
    }

    // Every change goes through here: a new list, so the bindings see it, stored a moment later.
    function update(list) {
        presets = list;
        edited = true;
        saveLater.restart();
        if (showLive.checked) {
            liveLater.restart();
        }
    }

    // A setting of the preset; undefined takes it out.
    function change(key, value) {
        const list = presets.slice();
        const p = Object.assign({}, list[current]);
        if (key === "name") {
            z20.renameApplied(p.name, value);
        }
        if (value === undefined) {
            delete p[key];
        } else {
            p[key] = value;
        }
        if (key === "effect") {  // the colors the effect takes; one at least where it needs one
            p.colors = (p.colors || []).slice(0, Presets.COLOR_SLOTS[value] || 0);
            if (Presets.COLOR_SLOTS[value] && !p.colors.length) {
                p.colors = ["ffffff"];
            }
            const ways = Presets.DIRECTIONS[value];
            p.direction = ways ? (ways.indexOf(p.direction) >= 0 ? p.direction : ways[0]) : undefined;
        }
        list[current] = p;
        update(list);
    }

    // The keys an effect runs on, as Unleash's zones: all, or some of Presets.ZONES (in their order).
    readonly property var zoneLabels: ({ numpad: i18n("Numpad"), fkeys: i18n("F keys"), numbers: i18n("Number row"),
                                         arrows: i18n("Arrows"), wasd: i18n("WASD"), bars: i18n("Light bars") })

    function zones() {
        return !preset || (preset.zone || "all") === "all" ? [] : preset.zone.split(",");
    }

    function setZone(name, on) {
        const list = zones().filter(z => z !== name).concat(on ? [name] : []);
        const ordered = Presets.ZONES.filter(z => list.indexOf(z) >= 0);
        change("zone", ordered.length ? ordered.join(",") : undefined);
    }

    function setColor(slot, color) {
        const colors = (preset.colors || []).slice();
        colors[slot] = color;
        change("colors", colors);
    }

    // Keys' own color (rrggbb, 000000 dark), or null: the effect shows there again.
    function setKeys(names, color) {
        const keys = Object.assign({}, preset.keys || {});
        names.forEach(name => {
            if (color === null) {
                delete keys[name];
            } else {
                keys[name] = color;
            }
        });
        change("keys", Object.keys(keys).length ? keys : undefined);
    }

    function move(step) {
        const to = current + step;
        if (to < 0 || to >= presets.length) {
            return;
        }
        const list = presets.slice();
        list.splice(to, 0, list.splice(current, 1)[0]);
        current = to;
        update(list);
    }

    onCurrentChanged: if (showLive.checked) liveLater.restart()

    // To try presets on the keyboard and to draw it: no reading in between.
    Lib.Z20Data {
        id: z20
        poll: false
    }

    // Stored a moment after the last change: a slider moved sends many.
    Timer {
        id: saveLater
        interval: 300
        onTriggered: z20.savePresets(page.presets)
    }

    // Changes shown on the keyboard as they're made: a moment after the last one.
    Timer {
        id: liveLater
        interval: 400
        onTriggered: if (page.preset) z20.applyPreset(page.preset, true)
    }

    // Colors for the effect and for the keys selected: the desktop's, the preset's, or any other.
    ColorPicker {
        id: picker

        property int slot: 0  // which of the effect's colors; -1: the selected keys'

        used: page.preset ? (page.preset.colors || []).concat(Object.values(page.preset.keys || {}))
            .filter((c, i, all) => all.indexOf(c) === i) : []
        onPicked: color => {
            if (slot < 0) {
                page.setKeys(keyboard.selected, color);
            } else {
                page.setColor(slot, color);
            }
        }
    }

    padding: Kirigami.Units.largeSpacing

    RowLayout {
        anchors.fill: parent
        spacing: Kirigami.Units.largeSpacing

        // The presets, in the popup's order; the one picked is edited on the right.
        ColumnLayout {
            spacing: Kirigami.Units.smallSpacing
            Layout.fillHeight: true
            Layout.preferredWidth: Kirigami.Units.gridUnit * 12
            Layout.maximumWidth: Kirigami.Units.gridUnit * 12

            Kirigami.Heading {
                level: 4
                text: i18n("Presets")
            }

            QQC2.ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                // A list's colors and a frame, as KDE's lists have.
                Kirigami.Theme.colorSet: Kirigami.Theme.View
                Kirigami.Theme.inherit: false
                background: Rectangle {
                    color: Kirigami.Theme.backgroundColor
                    border.color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                          Kirigami.Theme.textColor.b, 0.2)
                    radius: Kirigami.Units.cornerRadius
                }

                ListView {
                    model: page.presets
                    currentIndex: page.current
                    clip: true

                    delegate: QQC2.ItemDelegate {
                        id: item

                        // Its colors as a strip, as in the popup; none: gray, or black for off.
                        readonly property var colors: (modelData.colors || []).length ? modelData.colors
                            : [modelData.effect === "off" ? "000000" : "808080"]

                        width: ListView.view.width
                        highlighted: ListView.isCurrentItem
                        onClicked: page.current = index

                        contentItem: ColumnLayout {
                            spacing: Kirigami.Units.smallSpacing

                            RowLayout {
                                // The one applied (from the popup or here).
                                Kirigami.Icon {
                                    visible: index === page.appliedIndex
                                    source: "checkmark"
                                    color: item.highlighted ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                                    implicitWidth: Kirigami.Units.iconSizes.small
                                    implicitHeight: implicitWidth
                                }
                                QQC2.Label {
                                    text: modelData.name
                                    color: item.highlighted ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                                    font.bold: index === page.appliedIndex
                                    elide: Text.ElideRight
                                    Layout.fillWidth: true
                                }
                                QQC2.Label {
                                    text: (Presets.LABELS[modelData.effect] || "").replace(/ \(.*\)$/, "")
                                    color: item.highlighted ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                                    font: Kirigami.Theme.smallFont
                                    opacity: 0.7
                                }
                            }
                            Row {
                                id: strip
                                Layout.fillWidth: true
                                Layout.preferredHeight: Math.max(3, Math.round(Kirigami.Units.smallSpacing * 0.75))

                                Repeater {
                                    model: item.colors

                                    Rectangle {
                                        width: strip.width / item.colors.length
                                        height: strip.height
                                        color: "#" + modelData
                                    }
                                }
                            }
                        }
                    }
                }
            }

            RowLayout {
                spacing: 0

                QQC2.ToolButton {
                    icon.name: "list-add"
                    display: QQC2.AbstractButton.IconOnly
                    text: i18n("New")
                    onClicked: {
                        const list = page.presets.slice();
                        list.push(Object.assign({}, page.preset || {}, { name: i18n("New preset") }));
                        page.current = list.length - 1;
                        page.update(list);
                    }
                    QQC2.ToolTip.text: i18n("A new preset, as this one is")
                    QQC2.ToolTip.visible: hovered
                }
                QQC2.ToolButton {
                    icon.name: "list-remove"
                    display: QQC2.AbstractButton.IconOnly
                    text: i18n("Remove")
                    enabled: page.presets.length > 1
                    onClicked: {
                        const list = page.presets.slice();
                        list.splice(page.current, 1);
                        page.current = Math.min(page.current, list.length - 1);
                        page.update(list);
                    }
                    QQC2.ToolTip.text: text
                    QQC2.ToolTip.visible: hovered
                }
                QQC2.ToolButton {
                    icon.name: "go-up"
                    display: QQC2.AbstractButton.IconOnly
                    text: i18n("Move up")
                    enabled: page.current > 0
                    onClicked: page.move(-1)
                    QQC2.ToolTip.text: text
                    QQC2.ToolTip.visible: hovered
                }
                QQC2.ToolButton {
                    icon.name: "go-down"
                    display: QQC2.AbstractButton.IconOnly
                    text: i18n("Move down")
                    enabled: page.current < page.presets.length - 1
                    onClicked: page.move(1)
                    QQC2.ToolTip.text: text
                    QQC2.ToolTip.visible: hovered
                }
            }
            QQC2.Button {
                readonly property var missing: Presets.defaults()
                    .filter(d => !page.presets.some(p => p.name === d.name))
                icon.name: "edit-undo"
                text: i18n("Add Built-in Presets")
                enabled: missing.length > 0
                onClicked: page.update(page.presets.concat(missing))
                Layout.fillWidth: true
                QQC2.ToolTip.text: missing.length
                    ? i18n("Adds back: %1", missing.map(d => d.name).join(", ")) : i18n("All of them are there")
                QQC2.ToolTip.visible: hovered
            }
        }

        Kirigami.Separator {
            Layout.fillHeight: true
        }

        // The preset picked: on the keyboard, its effect, and keys with colors of their own.
        QQC2.ScrollView {
            id: editor
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth

            ColumnLayout {
                width: editor.availableWidth
                spacing: Kirigami.Units.largeSpacing

                // Its name, and trying it on the keyboard: beside it, or below where the window is narrow.
                GridLayout {
                    columns: width > Kirigami.Units.gridUnit * 40 ? 2 : 1
                    columnSpacing: Kirigami.Units.largeSpacing
                    Layout.fillWidth: true

                    RowLayout {
                        spacing: Kirigami.Units.largeSpacing
                        Layout.fillWidth: true

                        Kirigami.Heading {
                            level: 2
                            text: page.preset ? page.preset.name : ""
                            elide: Text.ElideRight
                            Layout.fillWidth: !applied.visible
                        }
                        QQC2.Label {
                            id: applied
                            visible: page.current === page.appliedIndex
                            text: i18n("Applied")
                            color: Kirigami.Theme.positiveTextColor
                            Layout.fillWidth: true
                        }
                    }
                    RowLayout {
                        spacing: Kirigami.Units.smallSpacing

                        QQC2.Button {
                            icon.name: "dialog-ok-apply"
                            text: i18n("Apply")
                            enabled: !!page.preset
                            onClicked: {
                                showLive.checked = false;
                                z20.applyPreset(page.preset, false);
                            }
                            QQC2.ToolTip.text: i18n("Stored in the active profile (a software effect: as z20's animate "
                                                    + "service runs it, also after login), as the popup applies it")
                            QQC2.ToolTip.visible: hovered
                        }
                        QQC2.Button {
                            icon.name: "media-playback-start"
                            text: i18n("Try on the Keyboard")
                            enabled: !showLive.checked && !!page.preset
                            onClicked: z20.applyPreset(page.preset, true)
                            QQC2.ToolTip.text: i18n("Only for now: \"Back to Stored\" brings back what the keyboard had")
                            QQC2.ToolTip.visible: hovered
                        }
                        QQC2.Button {
                            icon.name: "view-refresh"
                            text: i18n("Back to Stored")
                            onClicked: {
                                showLive.checked = false;
                                z20.restoreLighting();
                            }
                        }
                        QQC2.CheckBox {
                            id: showLive
                            text: i18n("Show every change")
                            onToggled: if (checked) liveLater.restart()
                            QQC2.ToolTip.text: i18n("On the keyboard, as it's made: only for now, like trying it. Applying a "
                                                    + "preset in the popup stores it.")
                            QQC2.ToolTip.visible: hovered
                        }
                    }
                }
                QQC2.Label {
                    visible: z20.commandError !== ""
                    text: z20.commandError
                    color: Kirigami.Theme.negativeTextColor
                    wrapMode: Text.Wrap
                    Layout.fillWidth: true
                }

                KeyboardView {
                    id: keyboard
                    visible: !!z20.leds
                    layout: z20.leds
                    preset: page.preset
                    Layout.fillWidth: true
                    Layout.preferredHeight: implicitHeight
                }
                QQC2.Label {
                    visible: !z20.leds
                    text: i18n("Drawing the keyboard, and giving keys their own colors, needs z20 from 2026-11-16 on "
                               + "(z20 leds).")
                    wrapMode: Text.Wrap
                    opacity: 0.7
                    Layout.fillWidth: true
                }

                // The effect, and beside it (below, where the window is narrow) the keys' own colors.
                GridLayout {
                    visible: !!page.preset
                    columns: width > Kirigami.Units.gridUnit * 40 ? 2 : 1
                    columnSpacing: Kirigami.Units.gridUnit * 2
                    rowSpacing: Kirigami.Units.largeSpacing
                    Layout.fillWidth: true

                    ColumnLayout {
                        spacing: Kirigami.Units.smallSpacing
                        Layout.alignment: Qt.AlignTop
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1  // the two columns alike

                        Kirigami.Heading {
                            level: 4
                            text: i18n("Effect")
                        }

                        // Labels on the right of their column, each shown with its field.
                        GridLayout {
                            columns: 2
                            columnSpacing: Kirigami.Units.smallSpacing
                            rowSpacing: Kirigami.Units.smallSpacing
                            Layout.fillWidth: true

                            readonly property bool hasColors: page.slots > 0
                            readonly property bool lit: !!page.preset && page.preset.effect !== "off"
                            readonly property bool hasSpeed: !!page.preset && Presets.HAS_CYCLE.indexOf(page.preset.effect) >= 0
                            readonly property var ways: page.preset ? Presets.DIRECTIONS[page.preset.effect] || [] : []
                            // The keyboard's own effects can wait for the first key press.
                            readonly property bool own: lit && !Presets.isSoftware(page.preset.effect)

                            QQC2.Label {
                                text: i18n("Name:")
                                Layout.alignment: Qt.AlignRight
                            }
                            QQC2.TextField {
                                text: page.preset ? page.preset.name : ""
                                onEditingFinished: if (text.trim() && text.trim() !== page.preset.name) page.change("name", text.trim())
                                Layout.fillWidth: true
                                Layout.maximumWidth: Kirigami.Units.gridUnit * 16
                            }

                            QQC2.Label {
                                text: i18n("Effect:")
                                Layout.alignment: Qt.AlignRight
                            }
                            QQC2.ComboBox {
                                model: Presets.EFFECTS.map(e => Presets.LABELS[e])
                                currentIndex: page.preset ? Presets.EFFECTS.indexOf(page.preset.effect) : -1
                                onActivated: index => page.change("effect", Presets.EFFECTS[index])
                            }

                            Item {
                                visible: effectNote.visible
                            }
                            QQC2.Label {
                                id: effectNote
                                visible: !!page.preset && page.preset.effect !== "off" && page.preset.effect !== "static"
                                text: page.preset && Presets.isSoftware(page.preset.effect)
                                    ? i18n("Runs on this computer: z20 works out the colors and sends them 25 times a "
                                           + "second (the z20-animate user service, also after login). It pauses while "
                                           + "the screen is locked; the profile's own lighting shows then.")
                                    : page.preset && Presets.SENSOR_EFFECTS.indexOf(page.preset.effect) >= 0
                                    ? i18n("The keyboard runs this effect itself, also as the welcome effect when you "
                                           + "come to the desk: its colors, direction and brightness are the same "
                                           + "there (Presence). It goes by the distance the presence sensor measures "
                                           + "(Explosion: its rings move, in jumps, as you come nearer or move away). "
                                           + "The drawing is a guess at how it looks.")
                                    : i18n("The keyboard runs this effect itself; the drawing comes close to it.")
                                font: Kirigami.Theme.smallFont
                                opacity: 0.7
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                                Layout.maximumWidth: Kirigami.Units.gridUnit * 18
                            }

                            QQC2.Label {
                                visible: parent.hasColors
                                text: i18n("Colors:")
                                Layout.alignment: Qt.AlignRight
                            }
                            RowLayout {
                                visible: parent.hasColors
                                spacing: Kirigami.Units.smallSpacing

                                Repeater {
                                    model: page.preset ? page.preset.colors || [] : []

                                    Rectangle {
                                        implicitWidth: Kirigami.Units.iconSizes.medium
                                        implicitHeight: implicitWidth
                                        radius: width / 4
                                        color: "#" + modelData
                                        border.width: 1
                                        border.color: Kirigami.Theme.disabledTextColor

                                        MouseArea {
                                            anchors.fill: parent
                                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                                            cursorShape: Qt.PointingHandCursor
                                            onClicked: event => {
                                                if (event.button === Qt.RightButton) {  // remove it
                                                    const colors = page.preset.colors.slice();
                                                    colors.splice(index, 1);
                                                    page.change("colors", colors);
                                                } else {
                                                    picker.slot = index;
                                                    picker.openAt(parent, modelData);
                                                }
                                            }
                                        }
                                    }
                                }
                                QQC2.ToolButton {
                                    id: addColor
                                    icon.name: "list-add"
                                    visible: !!page.preset && (page.preset.colors || []).length < page.slots
                                    onClicked: {
                                        picker.slot = (page.preset.colors || []).length;
                                        picker.openAt(addColor, "");
                                    }
                                    QQC2.ToolTip.text: i18n("Add a color")
                                    QQC2.ToolTip.visible: hovered
                                }
                            }

                            Item {
                                visible: colorsNote.visible
                            }
                            QQC2.Label {
                                id: colorsNote
                                visible: page.slots > 2
                                text: i18n("Click a color to change it, right-click to remove it. Fewer than %1 repeat.",
                                           page.slots)
                                font: Kirigami.Theme.smallFont
                                opacity: 0.7
                                wrapMode: Text.Wrap
                                Layout.fillWidth: true
                                Layout.maximumWidth: Kirigami.Units.gridUnit * 18
                            }

                            QQC2.Label {
                                visible: parent.lit
                                text: i18n("Brightness:")
                                Layout.alignment: Qt.AlignRight
                            }
                            RowLayout {
                                visible: parent.lit

                                QQC2.Slider {
                                    id: brightness
                                    from: 0
                                    to: 100
                                    stepSize: 5
                                    value: page.preset && page.preset.brightness !== undefined ? page.preset.brightness : 100
                                    onMoved: page.change("brightness", value)
                                    Layout.preferredWidth: Kirigami.Units.gridUnit * 10
                                }
                                QQC2.Label {
                                    text: i18n("%1 %", Math.round(brightness.value))
                                }
                            }

                            QQC2.Label {
                                visible: parent.hasSpeed
                                text: i18n("Speed:")
                                Layout.alignment: Qt.AlignRight
                            }
                            RowLayout {
                                visible: parent.hasSpeed

                                QQC2.Slider {
                                    id: cycle
                                    from: 200
                                    to: 10000
                                    stepSize: 100
                                    value: page.preset && page.preset.cycle ? page.preset.cycle : 3000
                                    onMoved: page.change("cycle", value)
                                    Layout.preferredWidth: Kirigami.Units.gridUnit * 10
                                }
                                QQC2.Label {
                                    text: i18n("%1 s per cycle", (cycle.value / 1000).toFixed(1))
                                }
                            }

                            QQC2.Label {
                                visible: parent.ways.length > 0
                                text: i18n("Direction:")
                                Layout.alignment: Qt.AlignRight
                            }
                            QQC2.ComboBox {
                                readonly property var ways: parent.ways
                                visible: ways.length > 0
                                model: ways
                                currentIndex: page.preset ? ways.indexOf(page.preset.direction) : -1
                                onActivated: index => page.change("direction", ways[index])
                                // A new model (wave ↔ spiral) puts the ComboBox on its first entry; back to the preset's.
                                onModelChanged: currentIndex = Qt.binding(() => page.preset ? ways.indexOf(page.preset.direction) : -1)
                            }

                            QQC2.Label {
                                visible: parent.own
                                text: i18n("Keys:")
                                Layout.alignment: Qt.AlignRight | Qt.AlignTop
                                Layout.topMargin: Kirigami.Units.smallSpacing
                            }
                            Flow {
                                visible: parent.own
                                spacing: Kirigami.Units.smallSpacing
                                Layout.fillWidth: true

                                QQC2.CheckBox {
                                    id: allKeys
                                    text: i18n("All")
                                    checked: page.zones().length === 0
                                    onToggled: {
                                        if (checked) {
                                            page.change("zone", undefined);
                                        }
                                        checked = Qt.binding(() => page.zones().length === 0);
                                    }
                                }
                                Repeater {
                                    model: Presets.ZONES

                                    QQC2.CheckBox {
                                        text: page.zoneLabels[modelData]
                                        checked: page.zones().indexOf(modelData) >= 0
                                        onToggled: {
                                            page.setZone(modelData, checked);
                                            checked = Qt.binding(() => page.zones().indexOf(modelData) >= 0);
                                        }
                                    }
                                }
                            }

                            QQC2.Label {
                                visible: parent.own
                                text: i18n("Stops:")
                                Layout.alignment: Qt.AlignRight
                            }
                            QQC2.ComboBox {
                                id: stopBox
                                readonly property var labels: [i18n("Never"), i18n("On a key press"),
                                                               i18n("When the key is let go")]
                                visible: parent.own
                                model: labels
                                currentIndex: page.preset ? Presets.STOPS.indexOf(page.preset.stop || "never") : 0
                                onActivated: index => {
                                    page.change("stop", index ? Presets.STOPS[index] : undefined);
                                    currentIndex = Qt.binding(() => page.preset
                                        ? Presets.STOPS.indexOf(page.preset.stop || "never") : 0);
                                }
                            }

                            QQC2.Label {
                                visible: !!page.preset && page.preset.effect === "reactive"
                                text: i18n("Lights:")
                                Layout.alignment: Qt.AlignRight
                            }
                            QQC2.ComboBox {
                                id: modeBox
                                visible: !!page.preset && page.preset.effect === "reactive"
                                model: [i18n("The key pressed"), i18n("One key"), i18n("3×3 around the key")]
                                currentIndex: page.preset
                                    ? Presets.REACTIVE_MODES.indexOf(page.preset.mode || "typed") : 0
                                onActivated: index => {
                                    page.change("mode", index ? Presets.REACTIVE_MODES[index] : undefined);
                                    currentIndex = Qt.binding(() => page.preset
                                        ? Presets.REACTIVE_MODES.indexOf(page.preset.mode || "typed") : 0);
                                }
                            }

                            QQC2.Label {
                                visible: !!page.preset && page.preset.effect === "reactive"
                                text: i18n("Fade out:")
                                Layout.alignment: Qt.AlignRight
                            }
                            RowLayout {
                                visible: !!page.preset && page.preset.effect === "reactive"

                                QQC2.Slider {
                                    id: fadeOut
                                    from: 0
                                    to: 100
                                    stepSize: 1
                                    value: page.preset && page.preset.fadeOut !== undefined ? page.preset.fadeOut
                                                                                            : Presets.FADE_OUT
                                    onMoved: page.change("fadeOut", value === Presets.FADE_OUT ? undefined : value)
                                    Layout.preferredWidth: Kirigami.Units.gridUnit * 10
                                }
                                QQC2.Label {
                                    text: fadeOut.value === 0 ? i18n("slowest") : fadeOut.value === 100
                                        ? i18n("at once") : String(Math.round(fadeOut.value))
                                }
                            }

                            QQC2.Label {
                                visible: parent.own
                                text: i18n("Starts:")
                                Layout.alignment: Qt.AlignRight
                            }
                            QQC2.CheckBox {
                                id: onKey
                                visible: parent.own
                                text: i18n("On the first key press")
                                checked: !!page.preset && !!page.preset.onKey
                                onToggled: {
                                    page.change("onKey", checked || undefined);
                                    checked = Qt.binding(() => !!page.preset && !!page.preset.onKey);
                                }
                                QQC2.ToolTip.text: i18n("Dark until then, also after the keyboard is plugged in, the "
                                                        + "lighting reloaded or the welcome effect played")
                                QQC2.ToolTip.visible: hovered
                            }
                        }
                    }

                    ColumnLayout {
                        visible: !!z20.leds
                        spacing: Kirigami.Units.smallSpacing
                        Layout.alignment: Qt.AlignTop
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1

                        Kirigami.Heading {
                            level: 4
                            text: i18n("Keys with Their Own Color")
                        }
                        QQC2.Label {
                            text: keyboard.selected.length
                                ? i18np("1 key selected", "%1 keys selected", keyboard.selected.length)
                                : i18n("Click keys on the drawing, or drag over them (with Ctrl to unselect), or pick "
                                       + "groups below; then give them a color.")
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                        RowLayout {
                            spacing: Kirigami.Units.smallSpacing
                            enabled: keyboard.selected.length > 0

                            QQC2.Button {
                                id: keysColor
                                icon.name: "color-picker"
                                text: i18n("Color…")
                                onClicked: {
                                    picker.slot = -1;
                                    picker.openAt(keysColor, (page.preset.keys || {})[keyboard.selected[0]]);
                                }
                            }
                            QQC2.Button {
                                text: i18n("Dark")
                                onClicked: page.setKeys(keyboard.selected, "000000")
                                QQC2.ToolTip.text: i18n("No light on these keys")
                                QQC2.ToolTip.visible: hovered
                            }
                            QQC2.Button {
                                text: i18n("The Effect")
                                enabled: keyboard.selected.some(n => page.preset.keys && page.preset.keys[n] !== undefined)
                                onClicked: page.setKeys(keyboard.selected, null)
                                QQC2.ToolTip.text: i18n("No color of their own: the effect shows on these keys")
                                QQC2.ToolTip.visible: hovered
                            }
                        }

                        QQC2.Label {
                            text: i18n("Groups:")
                            Layout.topMargin: Kirigami.Units.smallSpacing
                        }
                        // A group adds its keys to those selected, and takes them out again.
                        Flow {
                            spacing: Kirigami.Units.smallSpacing
                            Layout.fillWidth: true

                            Repeater {
                                model: z20.leds ? Keyboard.groups(z20.leds.leds) : []

                                QQC2.ToolButton {
                                    readonly property bool all: modelData.names.every(n => keyboard.selected.indexOf(n) >= 0)

                                    visible: modelData.names.length > 0
                                    text: modelData.name
                                    checkable: true
                                    checked: all
                                    onClicked: keyboard.select(modelData.names, !all)
                                }
                            }
                            QQC2.ToolButton {
                                icon.name: "edit-select-none"
                                text: i18n("None")
                                enabled: keyboard.selected.length > 0
                                onClicked: keyboard.selected = []
                            }
                        }

                        QQC2.Label {
                            visible: page.keyColors.length > 0
                            text: i18n("Own colors (a click selects their keys):")
                            Layout.topMargin: Kirigami.Units.smallSpacing
                        }
                        Flow {
                            visible: page.keyColors.length > 0
                            spacing: Kirigami.Units.smallSpacing
                            Layout.fillWidth: true

                            Repeater {
                                model: page.keyColors

                                QQC2.ToolButton {
                                    text: modelData.names.length
                                    onClicked: keyboard.selected = modelData.names
                                    QQC2.ToolTip.text: (modelData.color === "000000" ? i18n("Dark") : "#" + modelData.color)
                                        + ": " + modelData.names.join(", ")
                                    QQC2.ToolTip.visible: hovered

                                    contentItem: Row {
                                        spacing: Kirigami.Units.smallSpacing

                                        Rectangle {
                                            anchors.verticalCenter: parent.verticalCenter
                                            width: Kirigami.Units.iconSizes.small
                                            height: width
                                            radius: width / 4
                                            color: "#" + modelData.color
                                            border.width: 1
                                            border.color: Kirigami.Theme.disabledTextColor
                                        }
                                        QQC2.Label {
                                            anchors.verticalCenter: parent.verticalCenter
                                            text: modelData.names.length
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
