#!/usr/bin/python3

from gi import require_version
require_version("Gtk", "3.0")
require_version("Notify", "0.7")
from gi.repository import Gtk, Gdk, Gio, GLib, Notify
import pychromecast as pyc
import preferences
import threading
import subprocess
import time
import json

ext_dict = {'mp4':'video/mp4', 'webm':'video/webm'}

class ChromecastPlayer(Gtk.Application):

    def __init__(self, uri):
        Gtk.Application.__init__(self,
                                 application_id='org.gnome.chromecast-player',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name("Chromecast Player")
        GLib.set_prgname('chromecast-player')
        self.connect("activate", self.on_activate, uri)
        self.cast = None
        self.get_chromecast_config()
        self.uri = None
        self.play_uri = None
        self.uri_ext = None
        self.uri_working = False
        self.stop_worker = False
    
    def exit(self, *args):
        self.win.close()
        self.stop_worker = True
        self.quit()

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

        loadButtonImage = Gtk.Image()
        loadButtonImage.set_from_stock(Gtk.STOCK_OK, Gtk.IconSize.BUTTON)

        disconnectButtonImage = Gtk.Image()
        disconnectButtonImage.set_from_stock(Gtk.STOCK_DISCONNECT, Gtk.IconSize.BUTTON)

        vboxall = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hboxclient = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxprogress = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxbuttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxclose = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.win.add(vboxall)
        self.win.set_size_request(500,50)
        
        self.play = Gtk.Button()
        self.play.connect("clicked", self.on_play_clicked)
        self.play.add(playButtonImage)
        self.pause = Gtk.Button()
        self.pause.connect("clicked", self.on_pause_clicked)
        self.pause.add(pauseButtonImage)
        self.stop = Gtk.Button()
        self.stop.add(stopButtonImage)
        self.prev = Gtk.Button()
        self.prev.add(prevButtonImage)
        self.next = Gtk.Button()
        self.next.add(nextButtonImage)

        self.volume = Gtk.VolumeButton()

        self.progressbar = Gtk.HScale()
        self.progressbar.set_margin_left(6)
        self.progressbar.set_margin_right(6)
        self.progressbar.set_draw_value(False)
        self.progressbar.set_range(0, 100)
        self.progressbar.set_increments(1, 10)
        self.label = Gtk.Label(label='0:00/0:00')
        self.label.set_margin_left(6)
        self.label.set_margin_right(6)
        
        self.clientstore = Gtk.ListStore(str)
        self.clients_combo = Gtk.ComboBox.new_with_model(self.clientstore)
        self.get_active_chromecasts()

        if self.chromecasts:
            for cast in self.chromecasts:
                self.clientstore.append([cast])
            if self.automatic_connect:
                self.connect_to_chromecast(self.chromecasts[0])
                if self.cast:
                    self.cast.wait()
                    self.clients_combo.set_active(0)
            else:
                self.clients_combo.set_active(-1)
        else:
            self.clientstore.append([""])
            self.clients_combo.set_sensitive(False)
        
        self.clients_combo.connect("changed", self.combo_changed_clients)
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_fixed_size(120, 20)
        self.clients_combo.pack_start(renderer_text, True)
        self.clients_combo.add_attribute(renderer_text, "text", 0)
        refresh = Gtk.Button()
        refresh.add(refreshButtonImage)
        refresh.connect("clicked", self.refresh_chromecasts)

        load = Gtk.Button()
        load.add(loadButtonImage)
        load.connect("clicked", self.load_uri)

        disconnect = Gtk.Button()
        disconnect.add(disconnectButtonImage)
        disconnect.connect("clicked", self.disconnect_chromecasts)
        
        close = Gtk.Button("_Close", use_underline=True)
        close.get_style_context().add_class("destructive-action")
        close.connect("clicked", self.exit)
        
        hboxclient.pack_start(load, True, False, 2)
        hboxclient.pack_start(self.clients_combo, True, False, 2)
        hboxclient.pack_start(refresh, True, False, 2)
        hboxclient.pack_start(disconnect, True, False, 2)
        
        hboxprogress.pack_start(self.progressbar, True, True, 0)
        hboxprogress.pack_end(self.label, False, False, 0)
        hboxprogress.set_margin_left(10)
        
        hboxbuttons.pack_start(self.play, False, False, 2)
        hboxbuttons.pack_start(self.pause, False, False, 2)
        hboxbuttons.pack_start(self.stop, False, False, 2)
        hboxbuttons.pack_start(self.prev, False, False, 2)
        hboxbuttons.pack_start(self.next, False, False, 2)
        
        hboxbuttons.pack_end(hboxclient, False, False, 0)
        hboxbuttons.set_margin_left(10)
        hboxbuttons.set_margin_right(10)
        
        hboxclose.pack_start(self.volume, False, False, 30)
        hboxclose.pack_end(close, False, False, 30)
        vboxall.set_margin_top(10)
        vboxall.pack_start(hboxprogress, True, False, 0)
        vboxall.pack_start(hboxbuttons, True, False, 10)
        vboxall.pack_start(hboxclose, False, False, 10)

        mainmenu = Gtk.Menu()
        filem = Gtk.MenuItem("Open")
        mainmenu.append(filem)
        filem.connect('activate', self.on_file_clicked)
    
        streamm = Gtk.MenuItem("Open network stream")
        mainmenu.append(streamm)
        streamm.connect('activate', self.on_net_stream_clicked)
        
        prefm = Gtk.MenuItem("Preferences")
        mainmenu.append(prefm)
        prefm.connect('activate', self.on_preferences_clicked)

        exit = Gtk.MenuItem("Close")
        exit.connect("activate", self.exit)
        mainmenu.append(exit)

        root_menu = Gtk.MenuItem('File')
        root_menu.set_submenu(mainmenu)
        
        menu_bar = Gtk.MenuBar()
        menu_bar.append(root_menu)

        vboxall.pack_start(menu_bar, False, False, 2)
        self._worker_thread()
        GLib.timeout_add(100,self._worker_thread)
        self.win.show_all()
        self.add_window(self.win)


    def get_chromecast_config(self):
        chromecast_config = preferences.get_config('chromecast_player')
        self.automatic_connect = chromecast_config['automatic_connect']
        self.enable_web = chromecast_config['enable_web'] #unfortunately pychromecast doesn't allow to cast local files :(
        #might be something that is definitely worth adding in future versions


    def combo_changed_clients(self, widget):
        ind = widget.get_active()
        if ind == -1:
            return
        else:
            dev = self.chromecasts[ind]
        if not dev:
            return
        self.connect_to_chromecast(dev)
        if self.cast:
            self.cast.wait()
        else:
            self.clients_combo.set_active(-1)
            message = ("Cannot connect to chromecast. You sure you are still connected to the same network?")
            win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
            dialog = Gtk.MessageDialog(win, None, Gtk.MessageType.ERROR,
                           Gtk.ButtonsType.OK, message)
            dialog.run()
            dialog.destroy()
    
    def connect_to_chromecast(self, name):
        self.cast = pyc.get_chromecast(friendly_name=name)
        if self.cast:
            self.cast.wait()
            self.mc = self.cast.media_controller
        
    def disconnect_chromecasts(self, *args):
        if self.cast:
            self.cast.quit_app()
        self.clients_combo.set_active(-1)
    
    def on_file_clicked(self, *args):
        win = FileChooserWindow()
        ret = win.main()
        self.uri = ret
    
    def on_play_clicked(self, *args):
        if self.cast:
            if self.play_uri:
                if self.uri_ext not in ext_dict.keys():
                    self.play_uri = None
                    self.uri_ext = None
                    return
                self.mc.play_media(self.play_uri, ext_dict[self.uri_ext])
                self.play_uri = None
                self.uri_ext = None
            if self.mc.is_paused:
                self.mc.play()
    
    def on_pause_clicked(self, *args):
        if self.cast:
            if self.mc.is_playing:
                self.mc.pause()
    
    def on_net_stream_clicked(self, *args):
        win = NetworkStream()
        ret = win.main()
        thread = threading.Thread(target=self.get_network_uri, args=(ret,))
        thread.start()

    def get_network_uri(self, url):
        self.uri_working = True
        try:
            url2 = url[0]
            proc = subprocess.Popen(['youtube-dl', '-j', url], stdout=subprocess.PIPE)
            ret = proc.communicate()[0]
            dicti = json.loads(ret.decode('utf-8'))
            if 'youtube.com' in url:
                d = dicti['formats']
                res2 = d[0]['width']
                ind = 0
                for j, res in enumerate(d):
                    if not res['width']: continue
                    if not res2: res2 = res['width'] 
                    if res['width'] > res2:
                        res2 = res['width']
                        ind = j
                    elif res['width'] == res2:
                        if res['ext'] == 'mp4':
                            ind = j
                url = d[ind]['url']
                ext = dicti['ext']
            else:
                url = dicti['url']
                ext = dicti['ext']
        except:
            url = None
        self.uri_ext = ext
        self.uri = url
        self.uri_working = False

    def _worker_thread(self):
        if self.stop_worker:
            return False
        if self.cast:
            if self.mc.is_playing:
                self.progressbar.set_value(self.mc.status.current_time/self.mc.status.duration)
                self.label.set_label("%d:%d/%d:%d"%(int(self.mc.status.current_time/60), int(self.mc.status.current_time%60), int(self.mc.status.duration/60), int(self.mc.status.duration%60)))
                self.pause.set_sensitive(True)
                self.stop.set_sensitive(True)
                self.volume.set_sensitive(True)
                if self.mc.status.supports_skip_forward:
                    self.next.set_sensitive(True)
                else:
                    self.next.set_sensitive(False)
                if self.mc.status.supports_skip_backward:
                    self.prev.set_sensitive(True)
                else:
                    self.prev.set_sensitive(False)
                if not self.play_uri:
                    self.play.set_sensitive(False)
            elif self.mc.is_paused:
                self.progressbar.set_value(self.mc.status.current_time/self.mc.status.duration)
                self.label.set_label("%d:%d/%d:%d"%(int(self.mc.status.current_time/60), int(self.mc.status.current_time%60), int(self.mc.status.duration/60), int(self.mc.status.duration%60)))
                self.pause.set_sensitive(False)
                self.play.set_sensitive(True)
                self.volume.set_sensitive(True)
                self.stop.set_sensitive(True)
                if self.mc.status.supports_skip_forward:
                    self.next.set_sensitive(True)
                else:
                    self.next.set_sensitive(False)
                if self.mc.status.supports_skip_backward:
                    self.prev.set_sensitive(True)
                else:
                    self.prev.set_sensitive(False)
            elif self.mc.is_idle:
                self.label.set_label("0:00/0:00")
                self.stop.set_sensitive(False)
                self.volume.set_sensitive(False)
                self.prev.set_sensitive(False)
                self.next.set_sensitive(False)
                self.progressbar.set_value(0.)
                if not self.play_uri:
                    self.play.set_sensitive(False)
        else:
            self.label.set_label("0:00/0:00")
            self.pause.set_sensitive(False)
            self.volume.set_sensitive(False)
            self.stop.set_sensitive(False)
            self.prev.set_sensitive(False)
            self.next.set_sensitive(False)
            self.progressbar.set_value(0.)
            if self.play_uri:
                self.play.set_sensitive(True)
            else:
                self.play.set_sensitive(False)
        return True 
            

    def on_preferences_clicked(self, *args):
        preferences.Preferences()

    def load_uri(self, *args):
        while True:
            if not self.uri_working:
                break
            time.sleep(0.5)
        if not self.uri:
            self.play_uri = False
            Notify.init("chromecast-player")
            n = Notify.Notification.new("Chromecast-player", "Error loading stream. Make sure the stream you entered is valid", Gtk.STOCK_STOP)
            n.show()
            return
        self.play.set_sensitive(True)
        self.play_uri = self.uri

    def refresh_chromecasts(self, *args):
        self.clients_combo.handler_block_by_func(self.combo_changed_clients)
        ind = self.clients_combo.get_active()
        if ind != -1:
            cc_active = self.chromecasts[ind]
        else:
            cc_active = None
        self.get_active_chromecasts()
        self.clientstore.clear()
        if self.chromecasts:
            self.clients_combo.set_sensitive(True)
        else:
            self.clients_combo.set_sensitive(False)
        for cast in self.chromecasts:
            self.clientstore.append([cast])
        if cc_active in self.chromecasts and cc_active != "":
            ind = self.chromecasts.index(cc_active)
            self.clients_combo.set_active(ind)
        self.clients_combo.handler_unblock_by_func(self.combo_changed_clients)

    def get_active_chromecasts(self):
        casts = pyc.get_chromecasts_as_dict().keys()
        self.chromecasts = list(casts)
        return self.chromecasts

class FileChooserWindow(Gtk.Window):

    def __init__(self):
        self.win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    
    def main(self):
        dialog = Gtk.FileChooserDialog("Please choose a file", self.win,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        self.add_filters(dialog)
        ret = None
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            ret = dialog.get_uri()
        dialog.destroy()
        return ret
        

    def add_filters(self, dialog):
        filter_text = Gtk.FileFilter()
        filter_text.set_name("Supported Video/Audio files")
        filter_text.add_mime_type("video/mp4")
        filter_text.add_mime_type("audio/mp4")
        filter_text.add_mime_type("audio/mp3")
        filter_text.add_mime_type("audio/mpeg")
        filter_text.add_mime_type("video/webm")
        filter_text.add_mime_type("audio/webm")
        dialog.add_filter(filter_text)

class NetworkStream(Gtk.Window):

    def __init__(self):
        parent = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.win = Gtk.Dialog("My dialog",
                   parent,
                   Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                   (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OK   , Gtk.ResponseType.OK))
        self.ret = None
    
    def main(self):
        self.win.set_title("Enter URL for network stream")
        self.entry = Gtk.Entry()
        vboxall = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_size_request(500, 10)
        content_area = self.win.get_content_area()
        content_area.pack_start(self.entry, True, True, 10)
        self.entry.set_margin_left(10)
        self.entry.set_margin_right(10)
        self.entry.show()
        response = self.win.run()
        
        if response == Gtk.ResponseType.OK:
            self.ret = self.entry.get_text()
        self.win.destroy()
        return self.ret
        

