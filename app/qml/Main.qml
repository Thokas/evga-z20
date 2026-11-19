/*
 * The EVGA Z20 app (z20-settings): the keyboard's settings in a window of
 * their own, a page each, picked with the tabs at the top: the lighting
 * presets with the keys' own colors, macros, profile names, profiles for
 * programs, what happens when you leave, and the keyboard's own settings.
 * It opens on the page the command line names (startPage, which the Plasma
 * widget's pencils pass); run again, the launcher has the open one show
 * that page. A page with changes not saved (its dirty) asks before another
 * page or closing the window drops them.
 */

import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.ApplicationWindow {
    id: window

    // The pages in the tabs' order, by the name the command line uses.
    readonly property var pages: [
        { name: "lighting", source: "LightingPage.qml", title: i18n("Lighting"), icon: "preferences-desktop-color" },
        { name: "macros", source: "MacrosPage.qml", title: i18n("Macros"), icon: "media-record" },
        { name: "profiles", source: "ProfilesPage.qml", title: i18n("Profiles"), icon: "view-list-details" },
        { name: "programs", source: "ProgramsPage.qml", title: i18n("Programs"), icon: "applications-games" },
        { name: "presence", source: "PresencePage.qml", title: i18n("Presence"), icon: "user-away" },
        { name: "keyboard", source: "KeyboardPage.qml", title: i18n("Keyboard"), icon: "input-keyboard" }
    ]
    property string current: ""
    // What waits for the answer to "Discard Changes": the page to show, "" to close the window.
    property string pending: ""

    // A page by its name; another name, or none, the first.
    function showPage(name) {
        const page = pages.find(p => p.name === name) || pages[0];
        if (page.name !== current) {
            if (pageStack.currentItem && pageStack.currentItem.dirty) {
                tabs.currentIndex = Qt.binding(() => window.pages.findIndex(p => p.name === window.current));
                pending = page.name;
                discardDialog.open();
                return;
            }
            current = page.name;
            pageStack.clear();
            pageStack.push(Qt.resolvedUrl(page.source), { title: page.title });
        }
    }

    title: i18n("EVGA Z20")
    width: Kirigami.Units.gridUnit * 58
    height: Kirigami.Units.gridUnit * 44
    minimumWidth: Kirigami.Units.gridUnit * 40
    minimumHeight: Kirigami.Units.gridUnit * 26

    // The tab names the page: no title bar of its own.
    pageStack.globalToolBar.style: Kirigami.ApplicationHeaderStyle.None

    header: QQC2.TabBar {
        id: tabs
        position: QQC2.TabBar.Header
        currentIndex: window.pages.findIndex(p => p.name === window.current)

        Repeater {
            model: window.pages

            QQC2.TabButton {
                text: modelData.title
                icon.name: modelData.icon
                onClicked: window.showPage(modelData.name)
            }
        }
    }

    Kirigami.PromptDialog {
        id: discardDialog

        title: i18n("Discard Changes")
        subtitle: i18n("The changes on this page aren't saved yet.")
        standardButtons: Kirigami.Dialog.Cancel
        customFooterActions: [
            Kirigami.Action {
                text: i18n("Discard")
                icon.name: "edit-undo"
                onTriggered: {
                    discardDialog.close();
                    pageStack.clear();
                    if (window.pending) {
                        window.current = "";
                        window.showPage(window.pending);
                    } else {
                        window.close();
                    }
                }
            }
        ]
    }

    onClosing: close => {
        if (pageStack.currentItem && pageStack.currentItem.dirty) {
            close.accepted = false;
            pending = "";
            discardDialog.open();
        }
    }

    Component.onCompleted: showPage(startPage)
}
