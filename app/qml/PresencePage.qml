/*
 * The app's "Presence" page. First the keyboard's presence sensor: on or off
 * (in the active profile; off, neither the keyboard nor the service sees you),
 * what it sees now and the distance over the last two minutes. Then what
 * z20's presence service does when you leave the desk and come back (~/.config/z20/presence.ini, changed through `z20
 * presence set`): how long until you count as gone, locking the screen,
 * pausing media, the screens off, and the keyboard's lighting while you are
 * away (one of the lighting presets; the stored lighting comes back with
 * you). Below, what the keyboard itself does when you leave and when you
 * come (its welcome effect), stored in the active profile. Each change
 * applies at once; there is nothing to apply.
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
    readonly property bool sensorOn: wanted.sensorOn !== undefined ? wanted.sensorOn : !!sensor && sensor.on
    readonly property bool measured: !!sensor && sensor.on && sensor.distance_mm !== undefined
    // As the presence service goes by it: near, far or nothing in view (see Z20Data.seen).
    readonly property bool present: z20.seen === "near"
    readonly property bool outOfView: z20.seen === "nothing"
    readonly property bool nothing: measured && sensor.distance_mm >= 65000  // nothing in range
    // The presets to offer for the time away.
    readonly property var presets: Presets.parse(z20.presetsText)
    // Each preset as presence.ini's "away light", in the same order.
    readonly property var lights: presets.map(p => Presets.awayLight(p))
    readonly property string awayLight: settings ? settings.away_light || "" : ""
    // The away light is set but none of the presets (it was changed since, or set by hand).
    readonly property bool otherLight: awayLight !== "" && lights.indexOf(awayLight) < 0

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
    // id as z20 sensor welcome takes it, name as z20 sensor --json reads it.
    readonly property var welcomeChoices: [
        { id: "fade", name: "fade", text: i18n("Fade") },
        { id: "rows", name: "rows", text: i18n("Rows") },
        { id: "explosion", name: "explosion", text: i18n("Explosion") },
        { id: "raining", name: "raining", text: i18n("Raining") },
        { id: "barber", name: "barber pole", text: i18n("Barber pole") },
        { id: "lightbar", name: "light bar wave", text: i18n("Light bar wave") },
        { id: "thunder", name: "thunder", text: i18n("Thunder") }
    ]

    // What was just set here ({leave, come, sensorOn, keyboardLeave, keyboardAfter, welcome, welcomeMs}) until a
    // read has it (z20.settled), so a second change right after the first builds on it.
    property var wanted: ({})
    readonly property var leaveList: wanted.leave || (settings ? settings.leave : [])
    readonly property var comeList: wanted.come || (settings ? settings.come : [])
    readonly property string keyboardLeave: wanted.keyboardLeave || (sensor ? sensor.leave : "")
    readonly property int keyboardAfter: wanted.keyboardAfter || (sensor ? sensor.leave_after_s : 10)
    readonly property string welcome: wanted.welcome
        || (sensor ? (welcomeChoices.find(c => c.name === sensor.welcome) || { id: "" }).id : "")
    readonly property int welcomeMs: wanted.welcomeMs || (sensor ? sensor.welcome_ms : 5000)

    function want(changes) {
        wanted = Object.assign({}, wanted, changes);
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
        const leave = leaveList.filter(a => a.action !== id).concat(on ? [{ action: id, after_s: 0 }] : []);
        const changes = ["leave", actionList(leave)];
        let come = comeList;
        const back = { "pause-media": "resume-media", "screen-off": "wake" }[id];
        const has = !!back && comeList.some(a => a.action === back);
        if (back && on !== has && (on || back === "resume-media")) {
            come = comeList.filter(a => a.action !== back).concat(on ? [{ action: back, after_s: 0 }] : []);
            changes.push("come", actionList(come));
        }
        z20.setPresence(changes);
        want({ leave: leave, come: come });
    }

    function setSensorOn(on) {
        z20.setSensorOn(on);
        want({ sensorOn: on });
    }

    function setKeyboardLeave(action, seconds) {
        z20.setSensorLeave(action, seconds);
        want({ keyboardLeave: action, keyboardAfter: seconds });
    }

    function setWelcome(effect, ms) {
        z20.setSensorWelcome(effect, ms);
        want({ welcome: effect, welcomeMs: ms });
    }

    Lib.Z20Data {
        id: z20
        fast: true
        readSensor: true
        watchSensor: true
        onSettled: page.wanted = ({})
    }

    // Spin boxes send their value once it has stood still a moment, not at every step.
    Timer {
        id: awayAfter
        interval: 1000
        onTriggered: {
            z20.setPresence(["leave after", awayAfterBox.value]);
            awayAfterBox.value = Qt.binding(() => page.settings ? Math.round(page.settings.leave_after_s) : 30);
        }
    }
    Timer {
        id: keyboardAfter
        interval: 1000
        onTriggered: {
            page.setKeyboardLeave(page.keyboardLeave, keyboardAfterBox.value);
            keyboardAfterBox.value = Qt.binding(() => page.keyboardAfter);
        }
    }
    Timer {
        id: welcomeLength
        interval: 1000
        onTriggered: {
            page.setWelcome(page.welcome, welcomeLengthBox.value);
            welcomeLengthBox.value = Qt.binding(() => page.welcomeMs);
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
                page.setSensorOn(checked);
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

            readonly property real topMm: Math.max(z20.presentWithinMm * 2, 1000)  // the distance at the top edge
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
                const band = yOf(z20.presentWithinMm);
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
                anchors.bottomMargin: Math.min(parent.height - parent.yOf(z20.presentWithinMm) + 1,
                                               parent.height - height)
                text: i18n("%1 cm", Math.round(z20.presentWithinMm / 10))
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
            text: z20.presenceActive ? i18n("On") : i18n("Off")
            checked: z20.presenceActive
            onToggled: {
                z20.setPresenceService(checked);
                checked = Qt.binding(() => z20.presenceActive);
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
            visible: z20.presenceActive && !!page.sensor && !page.sensorOn
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
                value: page.settings ? Math.round(page.settings.leave_after_s) : 30
                onValueModified: awayAfter.restart()
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
                const light = index === 0 ? "" : index <= page.presets.length ? page.lights[index - 1] : page.awayLight;
                if (light !== page.awayLight) {
                    z20.setPresence(["away light", light]);
                }
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
                page.setKeyboardLeave(page.keyboardChoices[index].id, page.keyboardAfter);
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
                onValueModified: keyboardAfter.restart()
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
                page.setWelcome(page.welcomeChoices[index].id, page.welcomeMs);
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
                onValueModified: welcomeLength.restart()
            }
            QQC2.Label {
                text: i18nc("milliseconds", "ms")
            }
        }
        QQC2.Label {
            text: i18n("A lighting effect when the sensor sees you come to the desk; also when the keyboard is "
                       + "plugged in or the computer starts with you at the desk, as the sensor then sees you for "
                       + "the first time.")
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
