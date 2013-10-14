#!/usr/bin/env python
import sys
import os
import urllib
from PyQt5 import QtCore, QtGui, QtWebKit
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QPalette
from subprocess import Popen, PIPE


import time
import dbus
import re

# @TODO: change appPath method
appPath = os.path.dirname(os.path.realpath(__file__))
# @TODO: parse it from config
DEFAULT_FM = 'dolphin'
DEFAULT_BROWSER = "chromium-browser"
TIMER_INTERVAL = 1000
# @TODO: improve error reporting, then config parse will be done
DEFAULT_MSG = "<html><body>Error in template</body></html>"

metadata = {}


def shell_cmd(cmd):
    try:
        p = Popen(cmd, shell=True, stdout=PIPE)
        output = p.stdout.read()
    except:
        output = ''
    return output


class Browser:

    def dbus_reader(self):
        global metadata
        try:
            metadata = player.GetMetadata()
        except:
            metadata = False
        MSG = html_template
        # @TODO: create shell::{some command} parser
        MSG = MSG.replace('%UNAME%', shell_cmd('uname -a'))
        if metadata:
            MSG = MSG.replace('%ARTIST%', metadata['artist'])
            MSG = MSG.replace('%ALBUM%', metadata['album'])
            MSG = MSG.replace('%TITLE%', metadata['title'])
            MSG = MSG.replace('%ARTURL%', metadata['arturl'])
        self.web_view.setHtml(MSG)
        # list all available dbus parameters
        #for data in metadata:
        #    print data

    # ---------------------------------------------------------------- #
    # events - BEGIN
    # ---------------------------------------------------------------- #

    # event -  onLinkCliked
    def _on_navigation(self, url):
        url = str(url.toString().toUtf8())
        if self.on_command(url):
            return True
        else:
            #self.web_view.load(QUrl(url))
            return False

    # event -  onCompletePageLoading
    def _on_pageLoaded(self, ok):
        """
        will be fixed
        """
        self.width = geometry[2]
        self.window.setGeometry(geometry[0], geometry[1], geometry[2], geometry[3])
        self.window.show()
    # ---------------------------------------------------------------- #
    # events - END
    # ---------------------------------------------------------------- #

    def normalizeCmd(self, cmd):
        cmd = cmd.replace('cmd::', '')
        cmd = urllib.unquote_plus(cmd)
        cmd = os.path.expandvars(cmd)
        if 'defaultBrowser' in cmd:
            cmd = cmd.replace('defaultBrowser', DEFAULT_BROWSER)
        if 'defaultFileManager' in cmd:
            cmd = cmd.replace('defaultFileManager', DEFAULT_FM)

        return cmd

    def on_command(self, cmd):
        """
        parsing commands from html
        """
        if cmd.startswith('cmd::'):
            cmd = self.normalizeCmd(cmd)
            print(cmd)
            if cmd == 'exit':
                sys.exit()
            else:
                Popen(cmd, shell=True)
            return True
        else:
            return False

    def getDesktop(self):
        try:
            curDesktop = os.environ['XDG_CURRENT_DESKTOP']
        except:
            curDesktop = ''
        try:
            wmName = os.environ['DESKTOP_SESSION']
        except:
            wmName = ''
        return curDesktop.lower() if curDesktop != '' else wmName.lower()

    def __init__(self):
        """
        @TODO: clean it
        """
        global metadata
        self.app = QtGui.QApplication(sys.argv)
        self.window = QtGui.QMainWindow()
        # ------------------------------------------------------------ #
        desktop = self.getDesktop()
        print(desktop)
        # windowAttribute for openbox/pekwm WM
        if desktop in ['openbox', 'pekwm']:
            self.window.setAttribute(Qt.WA_X11NetWmWindowTypeDesktop)
        # windowAttribute for any other DE like xfce, gnome, unity, kde etc
        else:
            self.window.setAttribute(Qt.WA_X11NetWmWindowTypeDock)
            self.window.setWindowFlags(Qt.WindowStaysOnBottomHint)
        self.window.setAttribute(Qt.WA_TranslucentBackground)
        # ------------------------------------------------------------ #
        self.web_view = QtWebKit.QWebView()
        # trasparent webview
        palette = self.web_view.palette()
        palette.setBrush(QPalette.Base, Qt.transparent)
        self.web_view.page().setPalette(palette)
        self.web_view.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
        self.web_view.loadFinished.connect(self._on_pageLoaded)
        self.web_view.linkClicked.connect(self._on_navigation)
        self.window.setCentralWidget(self.web_view)
        #self.web_view.load(QUrl(self.default_site))
        self.web_view.setHtml(html_template)
        #self.web_view.show()
        self.dbus_timer = QtCore.QTimer()
        self.dbus_timer.start(TIMER_INTERVAL)
        QtCore.QObject.connect(self.dbus_timer, QtCore.SIGNAL("timeout()"), self.dbus_reader)
        #self.window.setCentralWidget(self.web_view)

    def main(self):
        sys.exit(self.app.exec_())


def readCmdLine():
    """
    here is will be config parsing, now it is placeholder
    """
    global html_template, geometry
    try:
        html_template = open('index.html', 'r').read()
    except:
        print('Error in template')
        html_template = DEFAULT_MSG
    try:
        l, t, w, h = (800, 30, 880, 600)
        geometry = (l, t, w, h)
        html_template = html_template.replace('%WIDTH%', str(w))
    except:
        print('Error in config')
    html_template = html_template.replace('%PATH%', appPath)


def connect_to_player(name):
    global root, player, tracklist
    # first we connect to the objects
    root_o = bus.get_object(name, "/")
    player_o = bus.get_object(name, "/Player")
    tracklist_o = bus.get_object(name, "/TrackList")
    # there is only 1 interface per object
    root = dbus.Interface(root_o, "org.freedesktop.MediaPlayer")
    tracklist = dbus.Interface(tracklist_o, "org.freedesktop.MediaPlayer")
    player = dbus.Interface(player_o, "org.freedesktop.MediaPlayer")
    # connect to the TrackChange signal
    #player_o.connect_to_signal("TrackChange", TrackChange, dbus_interface="org.freedesktop.MediaPlayer")
    return True


def init_dbus():
    global bus
    bus = dbus.SessionBus()
    while True:
        try:
            # @TODO: support other players via DBus or cli if DBus not supported
            connect_to_player('org.mpris.MediaPlayer2.clementine')
            break
        except:
            print('Cannot connect to Clementine via DBus')
            time.sleep(1)


if __name__ == '__main__':
    readCmdLine()
    init_dbus()
    browser = Browser()
    browser.main()
