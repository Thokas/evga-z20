/*
 * The app's "Presence" page. First the keyboard's presence sensor: on or off
 * (in the active profile; off, neither the keyboard nor the service sees you),
 * what it sees now and the distance over the last two minutes. Then z20's
 * presence service: whether it runs, and what it does when you leave the desk
 * and come back (~/.config/z20/presence.ini, through `z20 presence set`): how
 * long until you count as gone, locking the screen, pausing media, the
 * screens off, and the keyboard's lighting while you are away (one of the
 * lighting presets; the stored lighting comes back with you). Last, what the
 * keyboard itself does when you leave and when you come (its welcome effect,
 * with the effect's own colors), stored in the active profile.
 *
 * Changes wait for Save (Ctrl+S): the keyboard's then go in one profile write
 * (`z20 sensor` with all of them), presence.ini's in one `z20 presence set`,
 * which restarts the service once. Another page asks before it replaces
 * this one with changes not saved (Main.qml).
 */

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import org.kde.kcmutils as KCM

import "lib" as Lib
import "lib/presets.js" as Presets

KCM.SimpleKCM {
    id: page

    readonly property var settings: z20.presenceSettings
    readonly property var sensor: z20.sensor
    readonly property bool measured: !!sensor && sensor.on && sensor.distance_mm !== undefined
    // As the presence service goes by it: near, far or nothing in view (see Z20Data.seen).
    readonly property bool present: z20.seen === "near"
    readonly property bool outOfView: z20.seen === "nothing"
    readonly property bool nothing: measured && sensor.distance_mm >= 65000  // nothing in range
    // The presets to offer for the time away.
    readonly property var presets: Presets.parse(z20.presetsText)
    // Each preset as presence.ini's "away light", in the same order.
    readonly property var lights: presets.map(p => Presets.awayLight(p))

    readonly property var leaveChoices: [
        { id: "lock", text: i18n("Lock the screen") },
        { id: "pause-media", text: i18n("Pause media, and play it on when you're back") },
        { id: "screen-off", text: i18n("Turn the screens off") }
    ]
    readonly property var keyboardChoices: [
        { id: "nothing", text: i18n("Nothing") },
        { id: "dark", text: i18n("Lights off") },
        { id: "lock", text: i18n("Lock the screen (Win+L)") },
        { id: "sleep", text: i18n("Sleep") }
    ]
    // As z20 sensor welcome takes them and z20 sensor --json reads them (a z20 from before 2026-11-19 read the
    // barber pole and the light bar wave by their long names, the second).
    readonly property var welcomeChoices: [
        { id: "fade", text: i18n("Fade") },
        { id: "rows", text: i18n("Rows") },
        { id: "explosion", text: i18n("Explosion") },
        { id: "raining", text: i18n("Raining") },
        { id: "barber", old: "barber pole", text: i18n("Barber pole") },
        { id: "lightbar", old: "light bar wave", text: i18n("Light bar wave") },
        { id: "thunder", text: i18n("Thunder") }
    ]

    // As stored: what the page shows without changes.
    readonly property var saved: ({
        sensorOn: !!sensor && sensor.on,
        distance: sensor ? Math.round(sensor.distance_cm) : 50,
        serviceDistance: settings && settings.distance_cm ? settings.distance_cm : 0,
        serviceOn: z20.presenceActive,
        leaveAfter: settings ? Math.round(settings.leave_after_s) : 30,
        leave: settings ? settings.leave : [],
        come: settings ? settings.come : [],
        awayLight: settings ? settings.away_light || "" : "",
        keyboardLeave: sensor ? sensor.leave : "",
        keyboardAfter: sensor ? sensor.leave_after_s : 10,
        welcome: sensor ? (welcomeChoices.find(c => c.id === sensor.welcome || c.old === sensor.welcome)
                           || { id: "" }).id : "",
        welcomeMs: sensor ? sensor.welcome_ms : 5000
    })
    // The changes not saved yet, by those keys (and the welcome effect's own: welcomeColors, welcomeDirection,
    // welcomeBrightness), and what Save sent, until a read has it (z20.settled): a change right after Save
    // builds on it.
    property var draft: ({})
    property var sent: ({})
    readonly property var ownKeys: ({ welcomeColors: true, welcomeDirection: true, welcomeBrightness: true })
    readonly property bool dirty: Object.keys(draft).length > 0

    readonly property bool sensorOn: value("sensorOn")
    // Present: closer than the keyboard's distance (cm), which the service goes by too, unless presence.ini has
    // one of its own (serviceDistance, 0: none).
    readonly property int distance: value("distance")
    readonly property real serviceDistance: value("serviceDistance")
    readonly property real withinMm: (serviceDistance || distance) * 10
    readonly property bool serviceOn: value("serviceOn")
    readonly property int leaveAfter: value("leaveAfter")
    readonly property var leaveList: value("leave")
    readonly property var comeList: value("come")
    readonly property string awayLight: value("awayLight")
    // The away light is set but none of the presets (it was changed since, or set by hand).
    readonly property bool otherLight: awayLight !== "" && lights.indexOf(awayLight) < 0
    readonly property string keyboardLeave: value("keyboardLeave")
    readonly property int keyboardAfter: value("keyboardAfter")
    readonly property string welcome: value("welcome")
    readonly property int welcomeMs: value("welcomeMs")
    // The welcome effect's own colors (rrggbb; none for fade, rows and raining).
    // The welcome effect's own settings, as z20 sensor --json has them (welcome_effects): colors (rrggbb; none for
    // fade, rows and raining), direction (explosion: out, in; barber pole: left, right) and brightness (percent;
    // not for fade and rows, which have the lighting's).
    readonly property var welcomeColors: own("welcomeColors")
    readonly property string welcomeDirection: own("welcomeDirection")
    readonly property int welcomeBrightness: own("welcomeBrightness")
    readonly property var welcomeWays: ({ explosion: [["out", i18n("Outward")], ["in", i18n("Inward")]],
                                          barber: [["left", i18n("Left")], ["right", i18n("Right")]] })[welcome] || []

    function value(key) {
        return key in draft ? draft[key] : key in sent ? sent[key] : saved[key];
    }

    // One of the welcome effect's own settings: as changed, as sent, else as stored for that effect.
    function own(key) {
        return key in draft ? draft[key] : key in sent && sent.welcome === welcome ? sent[key] : stored(welcome, key);
    }

    function stored(id, key) {
        const e = sensor && sensor.welcome_effects ? sensor.welcome_effects[id] || {} : {};
        return key === "welcomeColors" ? (e.colors || []).map(c => c.replace("#", ""))
            : key === "welcomeDirection" ? e.direction || "" : e.brightness !== undefined ? e.brightness : -1;
    }

    // A change, kept until Save; back to what is stored, it is none.
    function change(key, v) {
        const d = Object.assign({}, draft);
        const before = key in ownKeys ? stored(welcome, key) : key in sent ? sent[key] : saved[key];
        if (JSON.stringify(v) === JSON.stringify(before)) {
            delete d[key];
        } else {
            d[key] = v;
        }
        draft = d;
    }

    function leaves(id) {
        return leaveList.some(a => a.action === id);
    }

    function actionList(list) {
        return list.map(a => a.action + (a.after_s ? " after " + a.after_s : "")).join(", ");
    }

    // One action on or off when you leave; the others keep their delays. Pausing media goes with resuming it,
    // the screens off with waking them.
    function setLeave(id, on) {
        change("leave", leaveList.filter(a => a.action !== id).concat(on ? [{ action: id, after_s: 0 }] : []));
        const back = { "pause-media": "resume-media", "screen-off": "wake" }[id];
        const has = !!back && comeList.some(a => a.action === back);
        if (back && on !== has && (on || back === "resume-media")) {
            change("come", comeList.filter(a => a.action !== back).concat(on ? [{ action: back, after_s: 0 }] : []));
        }
    }

    // Another welcome effect, with its own colors as stored.
    function setWelcome(id) {
        const d = Object.assign({}, draft);
        Object.keys(ownKeys).forEach(k => delete d[k]);
        draft = d;
        change("welcome", id);
    }

    function save() {
        const d = draft;
        const words = [];
        if ("sensorOn" in d) {
            words.push(d.sensorOn ? "on" : "off");
        }
        if ("distance" in d) {
            words.push("distance", distance);
        }
        if (("keyboardLeave" in d || "keyboardAfter" in d) && keyboardChoices.some(c => c.id === keyboardLeave)) {
            words.push("leave", keyboardLeave, keyboardAfter);
        }
        if (["welcome", "welcomeMs"].concat(Object.keys(ownKeys)).some(k => k in d) && welcome !== "") {
            words.push("welcome", welcome, welcomeMs, ...("welcomeColors" in d ? d.welcomeColors : []),
                       ...("welcomeDirection" in d ? [d.welcomeDirection] : []),
                       ...("welcomeBrightness" in d ? [d.welcomeBrightness + "%"] : []));
        }
        if (words.length) {
            z20.setSensor(words);
        }
        const changes = [];
        if ("leaveAfter" in d) {
            changes.push("leave after", leaveAfter);
        }
        if ("leave" in d) {
            changes.push("leave", actionList(leaveList));
        }
        if ("come" in d) {
            changes.push("come", actionList(comeList));
        }
        if ("awayLight" in d) {
            changes.push("away light", awayLight);
        }
        if ("serviceDistance" in d) {
            changes.push("distance", serviceDistance ? String(serviceDistance) : "");
        }
        if (changes.length) {
            z20.setPresence(changes);
        }
        if ("serviceOn" in d) {
            z20.setPresenceService(d.serviceOn);
        }
        sent = Object.assign({}, sent, d);
        draft = ({});
    }

    Lib.Z20Data {
        id: z20
        fast: true
        readSensor: true
        watchSensor: true
        onSettled: page.sent = ({})
    }

    // The welcome effect's colors: the desktop's, the effect's, or any other.
    ColorPicker {
        id: picker

        property int slot: 0

        used: page.welcomeColors.filter((c, i, all) => all.indexOf(c) === i)
        onPicked: color => {
            const colors = page.welcomeColors.slice();
            colors[slot] = color;
            page.change("welcomeColors", colors);
        }
    }

    Shortcut {
        sequences: [StandardKey.Save]
        enabled: page.dirty
        onActivated: page.save()
    }

    footer: QQC2.ToolBar {
        position: QQC2.ToolBar.Footer

        contentItem: RowLayout {
            QQC2.Label {
                text: z20.commandError || (page.dirty ? i18n("Not saved yet") : "")
                color: z20.commandError ? Kirigami.Theme.negativeTextColor : Kirigami.Theme.textColor
                elide: Text.ElideRight
                Layout.fillWidth: true
                Layout.leftMargin: Kirigami.Units.smallSpacing
            }
            QQC2.Button {
                icon.name: "edit-undo"
                text: i18n("Discard Changes")
                enabled: page.dirty
                onClicked: page.draft = ({})
            }
            QQC2.Button {
                id: saveButton
                icon.name: "document-save"
                text: i18n("Save")
                enabled: page.dirty
                onClicked: page.save()
            }
        }
    }

    Kirigami.FormLayout {
        Item {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: i18n("The keyboard's presence sensor")
        }

        QQC2.Switch {
            id: sensorSwitch
            Kirigami.FormData.label: i18n("Sensor:")
            text: page.sensorOn ? i18n("On") : i18n("Off")
            enabled: !!page.sensor
            checked: page.sensorOn
            onToggled: {
                page.change("sensorOn", checked);
                checked = Qt.binding(() => page.sensorOn);
            }
        }
        QQC2.Label {
            text: i18n("Stored in the active profile (%1). Off, the keyboard does nothing when you come and go, and "
                       + "the presence service below can't see you either.", z20.profile)
            font: Kirigami.Theme.smallFont
            wrapMode: Text.Wrap
            Layout.maximumWidth: Kirigami.Units.gridUnit * 24
        }

        RowLayout {
            Kirigami.FormData.label: i18n("Present within:")

            QQC2.SpinBox {
                id: distanceBox
                enabled: !!page.sensor
                from: 10
                to: 120
                value: page.distance
                onValueModified: {
                    page.change("distance", value);
                    value = Qt.binding(() => page.distance);
                }
            }
            QQC2.Label {
                text: i18n("cm")
            }
        }
        QQC2.Label {
            text: i18n("Closer than this counts as at the desk; farther away, as away. The keyboard goes by it, and "
                       + "so does the presence service. Between where you sit and where the empty chair stands: the "
                       + "graph below shows both.")
            font: Kirigami.Theme.smallFont
            wrapMode: Text.Wrap
            Layout.maximumWidth: Kirigami.Units.gridUnit * 24
        }

        RowLayout {
            Kirigami.FormData.label: i18n("Now:")
            spacing: Kirigami.Units.smallSpacing

            Kirigami.Icon {
                source: !page.sensor || !page.sensor.on ? "user-offline"
                    : page.outOfView ? "user-invisible" : page.present ? "user-online" : "user-away"
                implicitWidth: Kirigami.Units.iconSizes.smallMedium
                implicitHeight: implicitWidth
            }
            QQC2.Label {
                text: !page.sensor ? z20.readError || i18n("Reading…") : !page.sensor.on ? i18n("Sensor off")
                    : !page.measured ? i18n("Reading…")
                    : page.outOfView ? i18n("Nothing in view · leaning back, or nobody there")
                    : page.present ? i18n("At the desk · %1 cm", Math.round(page.sensor.distance_mm / 10))
                    : page.nothing ? i18n("Away · nothing in front of the sensor")
                    : i18n("Away · %1 cm", Math.round(page.sensor.distance_mm / 10))
            }
        }

        // The last two minutes: distance up, the keyboard at the bottom; inside the band counts as present.
        // Where nothing was in view, the line leaves a gap: the distance then means nothing.
        Canvas {
            id: graph

            readonly property real topMm: Math.max(page.withinMm * 2, 1000)  // the distance at the top edge
            onTopMmChanged: requestPaint()
            readonly property color lineColor: Kirigami.Theme.textColor
            readonly property color goodColor: Kirigami.Theme.positiveTextColor
            readonly property color awayColor: Kirigami.Theme.neutralTextColor

            visible: page.measured
            implicitWidth: Kirigami.Units.gridUnit * 24  // FormLayout goes by these, not by Layout's
            implicitHeight: Kirigami.Units.gridUnit * 4

            function yOf(mm) {
                return height - Math.min(mm, topMm) / topMm * (height - 2) - 1;
            }

            onPaint: {
                const ctx = getContext("2d");
                ctx.reset();
                const band = yOf(page.withinMm);
                ctx.fillStyle = Qt.rgba(goodColor.r, goodColor.g, goodColor.b, 0.12);
                ctx.fillRect(0, band, width, height - band);
                ctx.strokeStyle = Qt.rgba(goodColor.r, goodColor.g, goodColor.b, 0.6);
                ctx.setLineDash([4, 3]);
                ctx.beginPath();
                ctx.moveTo(0, band);
                ctx.lineTo(width, band);
                ctx.stroke();
                ctx.setLineDash([]);

                const now = Date.now();
                const points = z20.distances.map(d => [(d.t - now + 120000) / 120000 * (width - 4), yOf(d.mm),
                                                       d.inView !== false]);
                if (!points.length) {
                    return;
                }
                ctx.strokeStyle = Qt.rgba(lineColor.r, lineColor.g, lineColor.b, 0.8);
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                points.forEach((p, i) => p[2] && (i && points[i - 1][2] ? ctx.lineTo(p[0], p[1])
                                                                        : ctx.moveTo(p[0], p[1])));
                ctx.stroke();
                const last = points[points.length - 1];
                if (!last[2]) {
                    return;
                }
                ctx.fillStyle = page.present ? goodColor : awayColor;
                ctx.beginPath();
                ctx.arc(last[0], last[1], 3, 0, 2 * Math.PI);
                ctx.fill();
            }

            Connections {
                target: z20
                function onDistancesChanged() { graph.requestPaint(); }
            }
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()

            QQC2.Label {
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                anchors.bottomMargin: Math.min(parent.height - parent.yOf(page.withinMm) + 1,
                                               parent.height - height)
                text: i18n("%1 cm", Math.round(page.withinMm / 10))
                color: Kirigami.Theme.positiveTextColor
                font: Kirigami.Theme.smallFont
            }
            QQC2.Label {
                anchors.left: parent.left
                anchors.top: parent.top
                text: i18n("2 min")
                font: Kirigami.Theme.smallFont
                opacity: 0.5
            }
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: i18n("On the computer: z20's presence service")
        }

        Kirigami.InlineMessage {
            visible: !page.settings
            type: Kirigami.MessageType.Warning
            text: z20.detailsError || i18n("Reading the presence settings…")
            Layout.fillWidth: true
        }

        QQC2.Switch {
            Kirigami.FormData.label: i18n("Presence service:")
            id: serviceSwitch
            text: page.serviceOn ? i18n("On") : i18n("Off")
            checked: page.serviceOn
            onToggled: {
                page.change("serviceOn", checked);
                checked = Qt.binding(() => page.serviceOn);
            }
        }
        QQC2.Label {
            text: i18n("The service runs on the computer: it watches the keyboard's sensor and does what is set "
                       + "here each time you leave the desk and come back. The switch in the popup is the same.")
            font: Kirigami.Theme.smallFont
            wrapMode: Text.Wrap
            Layout.maximumWidth: Kirigami.Units.gridUnit * 24
        }
        Kirigami.InlineMessage {
            id: ownDistance
            visible: page.serviceDistance > 0
            type: Kirigami.MessageType.Information
            text: i18n("The service goes by a distance of its own, %1 cm (presence.ini), not the keyboard's.",
                       page.serviceDistance)
            actions: [
                Kirigami.Action {
                    text: i18n("Use the Keyboard's")
                    onTriggered: page.change("serviceDistance", 0)
                }
            ]
            Layout.fillWidth: true
        }
        Kirigami.InlineMessage {
            visible: page.serviceOn && !!page.sensor && !page.sensorOn
            type: Kirigami.MessageType.Warning
            text: i18n("The keyboard's sensor is off: the service can't see whether you are there.")
            Layout.fillWidth: true
        }

        RowLayout {
            Kirigami.FormData.label: i18n("Gone after:")

            QQC2.SpinBox {
                id: awayAfterBox
                enabled: !!page.settings
                from: 1
                to: 3600
                value: page.leaveAfter
                onValueModified: {
                    page.change("leaveAfter", value);
                    value = Qt.binding(() => page.leaveAfter);
                }
            }
            QQC2.Label {
                text: i18n("seconds away")
            }
        }

        ColumnLayout {
            Kirigami.FormData.label: i18n("When you leave:")
            spacing: 0

            Repeater {
                model: page.leaveChoices

                QQC2.CheckBox {
                    text: modelData.text
                    enabled: !!page.settings
                    checked: page.leaves(modelData.id)
                    onToggled: {
                        page.setLeave(modelData.id, checked);
                        checked = Qt.binding(() => page.leaves(modelData.id));
                    }
                }
            }
        }

        QQC2.ComboBox {
            Kirigami.FormData.label: i18n("Lighting while away:")
            enabled: !!page.settings
            model: [i18n("As it is")].concat(page.presets.map(p => p.name),
                                              page.otherLight ? [i18n("As set: %1", page.awayLight)] : [])
            currentIndex: !page.settings ? -1 : page.awayLight === "" ? 0
                : page.otherLight ? page.presets.length + 1 : page.lights.indexOf(page.awayLight) + 1
            onActivated: index => {
                page.change("awayLight", index === 0 ? "" : index <= page.presets.length ? page.lights[index - 1]
                                                                                          : page.awayLight);
                currentIndex = Qt.binding(() => !page.settings ? -1 : page.awayLight === "" ? 0
                    : page.otherLight ? page.presets.length + 1 : page.lights.indexOf(page.awayLight) + 1);
            }
        }
        QQC2.Label {
            text: i18n("A lighting preset that shows while you are away, without being stored; the stored "
                       + "lighting comes back with you. With nothing else on, that is all that happens when you "
                       + "leave.")
            font: Kirigami.Theme.smallFont
            wrapMode: Text.Wrap
            Layout.maximumWidth: Kirigami.Units.gridUnit * 24
        }
        Kirigami.InlineMessage {
            visible: page.leaves("lock") && Presets.isSoftware(page.awayLight.split(" ")[1] || "")
            type: Kirigami.MessageType.Information
            text: i18n("Software effects pause while the screen is locked, so with the lock the keyboard shows its "
                       + "stored lighting instead. Take one of the keyboard's own effects.")
            Layout.fillWidth: true
        }
        QQC2.Label {
            visible: !!page.settings && (page.settings.leave_run !== "" || page.settings.come_run !== "")
            text: !page.settings ? "" : [
                page.settings.leave_run ? i18n("When you leave, also: %1", page.settings.leave_run) : "",
                page.settings.come_run ? i18n("When you're back, also: %1", page.settings.come_run) : ""
            ].filter(s => s).join("\n")
            font: Kirigami.Theme.smallFont
            wrapMode: Text.Wrap
            Layout.maximumWidth: Kirigami.Units.gridUnit * 24
        }
        QQC2.Label {
            visible: !!page.settings
            text: page.settings ? i18n("Stored in %1.", page.settings.config) : ""
            font: Kirigami.Theme.smallFont
            opacity: 0.7
            wrapMode: Text.Wrap
            Layout.maximumWidth: Kirigami.Units.gridUnit * 24
        }

        Kirigami.Separator {
            Kirigami.FormData.isSection: true
            Kirigami.FormData.label: i18n("On the keyboard itself")
        }

        QQC2.ComboBox {
            Kirigami.FormData.label: i18n("When you leave:")
            enabled: !!page.sensor
            model: page.keyboardChoices.map(c => c.text)
            currentIndex: page.keyboardChoices.findIndex(c => c.id === page.keyboardLeave)
            onActivated: index => {
                page.change("keyboardLeave", page.keyboardChoices[index].id);
                currentIndex = Qt.binding(() => page.keyboardChoices.findIndex(c => c.id === page.keyboardLeave));
            }
        }
        RowLayout {
            Kirigami.FormData.label: i18n("After:")

            QQC2.SpinBox {
                id: keyboardAfterBox
                enabled: !!page.sensor && page.keyboardLeave !== "nothing"
                from: 10
                to: 999
                value: page.keyboardAfter
                onValueModified: {
                    page.change("keyboardAfter", value);
                    value = Qt.binding(() => page.keyboardAfter);
                }
            }
            QQC2.Label {
                text: i18n("seconds away")
            }
        }
        QQC2.Label {
            text: i18n("Only the first time you leave after the keyboard was plugged in or the profile was written. "
                       + "For every time, use the service above; its lighting can be hidden while the keyboard has "
                       + "turned its lights off here.")
            font: Kirigami.Theme.smallFont
            wrapMode: Text.Wrap
            Layout.maximumWidth: Kirigami.Units.gridUnit * 24
        }

        QQC2.ComboBox {
            id: welcomeBox
            Kirigami.FormData.label: i18n("When you come:")
            enabled: !!page.sensor
            model: page.welcomeChoices.map(c => c.text)
            currentIndex: page.welcomeChoices.findIndex(c => c.id === page.welcome)
            onActivated: index => {
                page.setWelcome(page.welcomeChoices[index].id);
                currentIndex = Qt.binding(() => page.welcomeChoices.findIndex(c => c.id === page.welcome));
            }
        }
        RowLayout {
            Kirigami.FormData.label: i18n("For:")

            QQC2.SpinBox {
                id: welcomeLengthBox
                enabled: !!page.sensor && page.welcome !== ""
                from: 500
                to: 30000
                stepSize: 500
                value: page.welcomeMs
                onValueModified: {
                    page.change("welcomeMs", value);
                    value = Qt.binding(() => page.welcomeMs);
                }
            }
            QQC2.Label {
                text: i18nc("milliseconds", "ms")
            }
        }
        RowLayout {
            Kirigami.FormData.label: i18n("Colors:")
            visible: page.welcomeColors.length > 0

            // As many as the effect with the most has, shown as far as this one has colors: a swatch the
            // Repeater took away while switching effects could still be measured by the next layout pass (a
            // crash, offscreen and in the app alike).
            Repeater {
                model: 7

                Rectangle {
                    visible: index < page.welcomeColors.length
                    implicitWidth: Kirigami.Units.iconSizes.medium
                    implicitHeight: implicitWidth
                    radius: width / 4
                    color: "#" + (page.welcomeColors[index] || "000000")
                    border.width: 1
                    border.color: Kirigami.Theme.disabledTextColor

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            picker.slot = index;
                            picker.openAt(parent, page.welcomeColors[index]);
                        }
                    }
                }
            }
        }
        QQC2.ComboBox {
            id: welcomeWay
            Kirigami.FormData.label: i18n("Direction:")
            visible: page.welcomeWays.length > 0
            model: page.welcomeWays.map(w => w[1])
            currentIndex: page.welcomeWays.findIndex(w => w[0] === page.welcomeDirection)
            onActivated: index => {
                page.change("welcomeDirection", page.welcomeWays[index][0]);
                currentIndex = Qt.binding(() => page.welcomeWays.findIndex(w => w[0] === page.welcomeDirection));
            }
        }
        RowLayout {
            Kirigami.FormData.label: i18n("Brightness:")
            visible: page.welcomeBrightness >= 0

            QQC2.Slider {
                id: welcomeLevel
                from: 0
                to: 100
                stepSize: 1
                value: Math.max(0, page.welcomeBrightness)
                onMoved: {
                    page.change("welcomeBrightness", value);
                    value = Qt.binding(() => Math.max(0, page.welcomeBrightness));
                }
                Layout.preferredWidth: Kirigami.Units.gridUnit * 10
            }
            QQC2.Label {
                text: i18n("%1 %", Math.round(welcomeLevel.value))
            }
        }
        Kirigami.InlineMessage {
            visible: page.welcome === "explosion"
            type: Kirigami.MessageType.Information
            text: i18n("Explosion follows the distance the sensor measures, not a clock: it stands still while you "
                       + "sit still, and its rings move, in jumps, as you come nearer or move away.")
            Layout.fillWidth: true
        }
        QQC2.Label {
            visible: page.welcome === "fade" || page.welcome === "rows"
            text: i18n("Its colors are those of the lighting effect of the same name.")
            font: Kirigami.Theme.smallFont
            wrapMode: Text.Wrap
            Layout.maximumWidth: Kirigami.Units.gridUnit * 24
        }
        QQC2.Label {
            text: i18n("A lighting effect when the sensor sees you come to the desk; also when the keyboard is "
                       + "plugged in or the computer starts with you at the desk, as the sensor then sees you for "
                       + "the first time. Colors that differ from the lighting stand out.")
            font: Kirigami.Theme.smallFont
            wrapMode: Text.Wrap
            Layout.maximumWidth: Kirigami.Units.gridUnit * 24
        }
        QQC2.Label {
            text: i18n("Stored in the active profile (%1). The keyboard does this by itself, without the service.",
                       z20.profile)
            font: Kirigami.Theme.smallFont
            opacity: 0.7
            wrapMode: Text.Wrap
            Layout.maximumWidth: Kirigami.Units.gridUnit * 24
        }
    }
}
