/*
 * The EVGA Z20 app (z20-settings): the keyboard's settings in a window of
 * their own, a page each, picked on the left: the lighting presets with the
 * keys' own colors, macros, profile names, profiles for programs, what
 * happens when you leave, and the keyboard's own settings. It opens on the
 * page the command line names (startPage, which the Plasma widget's pencils
 * pass); run again, the launcher has the open one show that page.
 */

import QtQuick
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: window

    // Each page: its file and title, by the name the command line uses.
    readonly property var pages: ({
        lighting: { source: "LightingPage.qml", title: i18n("Lighting") },
        macros: { source: "MacrosPage.qml", title: i18n("Macros") },
        profiles: { source: "ProfilesPage.qml", title: i18n("Profiles") },
        programs: { source: "ProgramsPage.qml", title: i18n("Programs") },
        presence: { source: "PresencePage.qml", title: i18n("Presence") },
        keyboard: { source: "KeyboardPage.qml", title: i18n("Keyboard") }
    })
    property string current: ""

    // A page by its name; another name, or none, the first.
    function showPage(name) {
        const shown = pages[name] ? name : "lighting";
        if (shown !== current) {
            current = shown;
            pageStack.clear();
            pageStack.push(Qt.resolvedUrl(pages[shown].source), { title: pages[shown].title });
        }
    }

    title: i18n("EVGA Z20")
    width: Kirigami.Units.gridUnit * 58
    height: Kirigami.Units.gridUnit * 44
    minimumWidth: Kirigami.Units.gridUnit * 34
    minimumHeight: Kirigami.Units.gridUnit * 26

    globalDrawer: Kirigami.GlobalDrawer {
        title: i18n("EVGA Z20")
        titleIcon: "input-keyboard"
        modal: !window.wideScreen
        width: Kirigami.Units.gridUnit * 11

        actions: [
            Kirigami.Action {
                text: window.pages.lighting.title
                icon.name: "preferences-desktop-color"
                checked: window.current === "lighting"
                onTriggered: window.showPage("lighting")
            },
            Kirigami.Action {
                text: window.pages.macros.title
                icon.name: "media-record"
                checked: window.current === "macros"
                onTriggered: window.showPage("macros")
            },
            Kirigami.Action {
                text: window.pages.profiles.title
                icon.name: "view-list-details"
                checked: window.current === "profiles"
                onTriggered: window.showPage("profiles")
            },
            Kirigami.Action {
                text: window.pages.programs.title
                icon.name: "applications-games"
                checked: window.current === "programs"
                onTriggered: window.showPage("programs")
            },
            Kirigami.Action {
                text: window.pages.presence.title
                icon.name: "user-away"
                checked: window.current === "presence"
                onTriggered: window.showPage("presence")
            },
            Kirigami.Action {
                text: window.pages.keyboard.title
                icon.name: "input-keyboard"
                checked: window.current === "keyboard"
                onTriggered: window.showPage("keyboard")
            }
        ]
    }

    Component.onCompleted: showPage(startPage)
}
