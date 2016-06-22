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
        

        playButtonImage = Gtk.Image()
        playButtonImage.set_from_stock(Gtk.STOCK_MEDIA_PLAY, Gtk.IconSize.BUTTON)

        pauseButtonImage = Gtk.Image()
        pauseButtonImage.set_from_stock(Gtk.STOCK_MEDIA_PAUSE, Gtk.IconSize.BUTTON)

        stopButtonImage = Gtk.Image()
        stopButtonImage.set_from_stock(Gtk.STOCK_MEDIA_STOP, Gtk.IconSize.BUTTON)

        prevButtonImage = Gtk.Image()
        prevButtonImage.set_from_stock(Gtk.STOCK_MEDIA_PREVIOUS, Gtk.IconSize.BUTTON)

        nextButtonImage = Gtk.Image()
        nextButtonImage.set_from_stock(Gtk.STOCK_MEDIA_NEXT, Gtk.IconSize.BUTTON)

        refreshButtonImage = Gtk.Image()
        refreshButtonImage.set_from_stock(Gtk.STOCK_REFRESH, Gtk.IconSize.BUTTON)

        disconnectButtonImage = Gtk.Image()
        disconnectButtonImage.set_from_stock(Gtk.STOCK_DISCONNECT, Gtk.IconSize.BUTTON)

        vboxall = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hboxclient = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxprogress = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxbuttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxclose = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.win.add(vboxall)
        self.win.set_size_request(500,50)
        
        play = Gtk.Button()
        play.add(playButtonImage)
        pause = Gtk.Button()
        pause.add(pauseButtonImage)
        stop = Gtk.Button()
        stop.add(stopButtonImage)
        prev = Gtk.Button()
        prev.add(prevButtonImage)
        next = Gtk.Button()
        next.add(nextButtonImage)

        progressbar = Gtk.HScale()
        progressbar.set_margin_left(6)
        progressbar.set_margin_right(6)
        progressbar.set_draw_value(False)
        progressbar.set_range(0, 100)
        progressbar.set_increments(1, 10)
        self.label = Gtk.Label(label='0:00')
        self.label.set_margin_left(6)
        self.label.set_margin_right(6)
        
        clientstore = Gtk.Entry()
        refresh = Gtk.Button()
        refresh.add(refreshButtonImage)
        disconnect = Gtk.Button()
        disconnect.add(disconnectButtonImage)
        
        close = Gtk.Button("_Close", use_underline=True)
        
        hboxclient.pack_start(clientstore, True, False, 2)
        hboxclient.pack_start(refresh, True, False, 2)
        hboxclient.pack_start(disconnect, True, False, 2)
        
        hboxprogress.pack_start(progressbar, True, True, 0)
        hboxprogress.pack_end(self.label, False, False, 0)
        hboxprogress.set_margin_left(10)
        
        hboxbuttons.pack_start(play, False, False, 2)
        hboxbuttons.pack_start(pause, False, False, 2)
        hboxbuttons.pack_start(stop, False, False, 2)
        hboxbuttons.pack_start(prev, False, False, 2)
        hboxbuttons.pack_start(next, False, False, 2)
        hboxbuttons.pack_end(hboxclient, False, False, 0)
        hboxbuttons.set_margin_left(10)
        hboxbuttons.set_margin_right(10)
        
        hboxclose.pack_end(close, False, False, 30)
        vboxall.set_margin_top(10)
        vboxall.pack_start(hboxprogress, True, False, 0)
        vboxall.pack_start(hboxbuttons, True, False, 10)
        vboxall.pack_start(hboxclose, False, False, 10)
        
        self.win.show_all()
        self.add_window(self.win)
        
