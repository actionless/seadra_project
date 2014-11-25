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
DEFAULT_FM = 'dolphin'
DEFAULT_BROWSER = "chromium-browser"
LEFT, TOP, WIDTH, HEIGHT = (600, 30, 680, 600)
# @TODO: improve error reporting, then config parse will be done
DEFAULT_MSG = "<html><body>Error in template</body></html>"


def get_desktop_name():
    current_desktop = os.environ.get('XDG_CURRENT_DESKTOP', '')
    desktop_session = os.environ.get('DESKTOP_SESSION', '')
    return current_desktop.lower() if current_desktop != '' \
        else desktop_session.lower()


def normalize_command(cmd):
    cmd = cmd.replace('cmd::', '')
    cmd = urllib.parse.unquote_plus(cmd)
    cmd = os.path.expandvars(cmd)
    if 'defaultBrowser' in cmd:
        cmd = cmd.replace('defaultBrowser', DEFAULT_BROWSER)
    if 'defaultFileManager' in cmd:
        cmd = cmd.replace('defaultFileManager', DEFAULT_FM)
    return cmd


def handle_command(cmd):
    """
    parsing commands from html
    """
    if cmd.startswith('cmd::'):
        cmd = normalize_command(cmd)
        print(cmd)
        if cmd == 'exit':
            sys.exit()
        else:
            Popen(cmd, shell=True)
        return True
    else:
        return False


def shell_cmd(cmd):
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


class Application:

    bus = None
    session_bus_connection = None
    dbus_message_handler = None
    player = None
    root = None
    tracklist = None

    html_template = None
    geometry = None

    # event -  onLinkCliked
    def on_navigation(self, url):
        url = str(url.toString())
        if handle_command(url):
            return True
        else:
            self.web_view.load(QUrl(url))
            return False

    def dbus_reader(self, msg):
        metadata = msg.arguments()[0]
        output = self.html_template
        # @TODO: create shell::{some command} parser
        # MSG = MSG.replace('%UNAME%', shell_cmd('uname -a').decode('UTF-8'))
        if metadata:
            output = output.replace('%ARTIST%', metadata['artist'])
            output = output.replace('%ALBUM%', metadata['album'])
            output = output.replace('%TITLE%', metadata['title'])
            output = output.replace('%ARTURL%', metadata['arturl'])
        self.web_view.setHtml(output)

    def init_dbus(self):
        self.session_bus_connection = QDBusConnection.sessionBus()

        service_name = 'org.mpris.MediaPlayer2.clementine'
        service_path = '/Player'
        interface_name = 'org.freedesktop.MediaPlayer'
        signal_name = 'TrackChange'

        self.player = QDBusInterface(
            service_name, service_path, interface_name,
            self.session_bus_connection)
        self.dbus_reader(self.player.call('GetMetadata'))

        self.dbus_message_handler = DBusMsgHandler(self.dbus_reader)
        self.session_bus_connection.connect(
            None, None, interface_name, signal_name,
            self.dbus_message_handler.handle)

    def read_config(self):
        try:
            self.html_template = open('index.html', 'r').read()
        except Exception:
            print('Error in template')
            self.html_template = DEFAULT_MSG

        # @TODO: here it will be config parsing, now it's a placeholder
        try:
            self.geometry = (LEFT, TOP, WIDTH, HEIGHT)
            self.html_template = self.html_template.replace(
                '%WIDTH%', str(WIDTH))
        except Exception:
            print('Error in config')
        self.html_template = self.html_template.replace('%PATH%', APP_PATH)

    def __init__(self):
        self.read_config()

        self.app = QApplication(sys.argv)
        self.window = QMainWindow()

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

        self.init_dbus()

        sys.exit(self.app.exec_())


if __name__ == '__main__':
    application = Application()