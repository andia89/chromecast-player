#!/usr/bin/python3

from gi import require_version
require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio, GLib



class ChromecastPlayer(Gtk.Application):

    def __init__(self, uri):
        Gtk.Application.__init__(self,
                                 application_id='org.gnome.chromecast-player',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name("Chromecast Player")
        GLib.set_prgname('chromecast-player')
        self.connect("activate", self.on_activate, uri)
    
    def on_activate(self, app, uri):
        self.win = Gtk.ApplicationWindow(Gtk.WindowType.TOPLEVEL, application=app)
        self.win.set_icon_name('chromecast-player')
        
        vboxall = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vboxclient = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hboxclient = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxprogress = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxbuttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxclose = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.win.add(vboxall)
        
        play = Gtk.Button()
        pause = Gtk.Button()
        stop = Gtk.Button()
        prev = Gtk.Button()
        next = Gtk.Button()
        progressbar = Gtk.ProgressBar()
        
        clientstore = Gtk.Button()
        refresh = Gtk.Button()
        disconnect = Gtk.Button()
        
        close = Gtk.Button()
        
        vboxclient.pack_start(disconnect, True, False, 0)
        vboxclient.pack_start(refresh, True, False, 0)
        
        hboxclient.pack_start(clientstore, True, False, 0)
        hboxclient.pack_start(vboxclient, True, False, 0)
        
        hboxprogress.pack_start(progressbar, True, False, 0)
        
        hboxbuttons.pack_start(play, True, False, 0)
        hboxbuttons.pack_start(pause, True, False, 0)
        hboxbuttons.pack_start(stop, True, False, 0)
        hboxbuttons.pack_start(prev, True, False, 0)
        hboxbuttons.pack_start(next, True, False, 0)
        hboxbuttons.pack_start(hboxclient, True, False, 0)
        
        hboxclose.pack_start(close, True, False, 0)
        
        vboxall.pack_start(hboxprogress, True, False, 0)
        vboxall.pack_start(hboxbuttons, True, False, 0)
        vboxall.pack_start(hboxclose, True, False, 0)
        
        self.win.show_all()
        self.add_window(self.win)
        
