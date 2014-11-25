#!/usr/bin/env python3
import sys
import os
import urllib.parse
from subprocess import Popen, PIPE

from PyQt5.QtCore import Qt, QUrl, QObject, pyqtSlot
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtGui import QPalette
from PyQt5.QtWebKitWidgets import QWebView, QWebPage
from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusMessage


APP_PATH = os.path.dirname(os.path.realpath(__file__))
# @TODO: parse it from config
SETTINGS = {
    "filemanager": 'dolphin',
    "browser": "chromium-browser",
    "right": 30,
    "top": 30,
    "width": 680,
    "height": 600,
}
# @TODO: improve error reporting, then config parse will be done
DEFAULT_MSG = "<html><body>Error in template</body></html>"


def get_desktop_name():
    current_desktop = os.environ.get('XDG_CURRENT_DESKTOP', '')
    desktop_session = os.environ.get('DESKTOP_SESSION', '')
    return current_desktop.lower() if current_desktop != '' \
        else desktop_session.lower()


def shell_cmd(self, cmd):
    try:
        output = Popen(cmd, shell=True, stdout=PIPE).stdout.read()
    except Exception:
        output = ''
    return output


class DBusMsgHandler(QObject):
    callback = None

    def __init__(self, callback):
        self.callback = callback
        super(DBusMsgHandler, self).__init__()

    @pyqtSlot(QDBusMessage)
    def handle(self, msg):
        self.callback(msg)


class CommandsHandler(object):
    settings = None

    def normalize_command(self, cmd):
        cmd = cmd.replace('cmd::', '')
        cmd = urllib.parse.unquote_plus(cmd)
        cmd = os.path.expandvars(cmd)
        if 'defaultBrowser' in cmd:
            cmd = cmd.replace(
                'defaultBrowser', self.settings["browser"])
        if 'defaultFileManager' in cmd:
            cmd = cmd.replace(
                'defaultFileManager', self.settings["filemanager"])
        return cmd

    def handle_command(self, cmd):
        """
        parsing commands from html
        """
        if cmd.startswith('cmd::'):
            cmd = self.normalize_command(cmd)
            print(cmd)
            if cmd == 'exit':
                sys.exit()
            else:
                Popen(cmd, shell=True)
            return True
        else:
            return False


class ClementineDBusInterface(object):
    application = None

    session_bus_connection = None
    dbus_message_handler = None

    player_interface = None
    root_interface = None
    tracklist_interface = None

    def dbus_reader(self, msg):
        self.application.metadata.update(msg.arguments()[0])
        self.application.render_template()

    def __init__(self, application):
        self.application = application

        service_name = 'org.mpris.MediaPlayer2.clementine'
        service_path = '/Player'
        interface_name = 'org.freedesktop.MediaPlayer'
        signal_name = 'TrackChange'

        self.session_bus_connection = QDBusConnection.sessionBus()

        self.player = QDBusInterface(
            service_name, service_path, interface_name,
            self.session_bus_connection)
        self.dbus_reader(self.player.call('GetMetadata'))

        self.dbus_message_handler = DBusMsgHandler(self.dbus_reader)
        self.session_bus_connection.connect(
            None, None, interface_name, signal_name,
            self.dbus_message_handler.handle)


class Application(CommandsHandler):

    settings = None

    metadata = None

    html_template = None
    screen_geometry = None
    geometry = None

    # event -  onLinkCliked
    def on_navigation(self, url):
        url = str(url.toString())
        if self.handle_command(url):
            return True
        else:
            self.web_view.load(QUrl(url))
            return False

    def render_template(self):
        metadata = self.metadata
        output = self.html_template
        # @TODO: create shell::{some command} parser
        # MSG = MSG.replace('%UNAME%', shell_cmd('uname -a').decode('UTF-8'))
        if metadata:
            output = output.replace('%ARTIST%', metadata['artist'])
            output = output.replace('%ALBUM%', metadata['album'])
            output = output.replace('%TITLE%', metadata['title'])
            output = output.replace('%ARTURL%', metadata['arturl'])
        self.web_view.setHtml(output)

    def read_config(self):
        # @TODO: here it will be config parsing, now it's a placeholder

        self.settings = SETTINGS

        try:
            self.html_template = open('index.html', 'r').read()
        except Exception:
            print('Error in template')
            self.html_template = DEFAULT_MSG

        left = self.settings.get(
            "left",
            self.screen_geometry.width() -
            self.settings["right"] - self.settings["width"]
        )
        self.geometry = (
            left, self.settings["top"],
            self.settings["width"], self.settings["height"]
        )
        self.html_template = self.html_template.replace(
            '%WIDTH%', str(self.settings["width"]))
        self.html_template = self.html_template.replace('%PATH%', APP_PATH)

    def __init__(self):

        self.app = QApplication(sys.argv)
        self.screen_geometry = self.app.desktop().screenGeometry()
        self.window = QMainWindow()

        self.read_config()
        self.metadata = {}

        if get_desktop_name() in ['openbox', 'pekwm']:
            # windowAttribute for openbox/pekwm WM
            self.window.setAttribute(Qt.WA_X11NetWmWindowTypeDesktop)
        else:
            # windowAttribute for any other DE like xfce, gnome, unity, kde etc
            self.window.setAttribute(Qt.WA_X11NetWmWindowTypeDock)
            self.window.setWindowFlags(Qt.WindowStaysOnBottomHint)
        self.window.setAttribute(Qt.WA_TranslucentBackground)

        self.web_view = QWebView()

        # trasparent webview
        palette = self.web_view.palette()
        palette.setBrush(QPalette.Base, Qt.transparent)
        self.web_view.page().setPalette(palette)

        self.web_view.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.web_view.linkClicked.connect(self.on_navigation)
        self.web_view.setHtml(self.html_template)

        self.window.setGeometry(self.geometry[0], self.geometry[1],
                                self.geometry[2], self.geometry[3])
        self.window.setCentralWidget(self.web_view)
        self.window.show()

        self.clementine = ClementineDBusInterface(self)

        sys.exit(self.app.exec_())


if __name__ == '__main__':
    application = Application()
