#!/usr/bin/python3

from gi import require_version
require_version("Gtk", "3.0")
require_version("Notify", "0.7")
from gi.repository import Gtk, Gdk, Gio, GLib, Notify
from urllib.parse import urlparse, unquote
import pychromecast as pyc
import preferences
import threading
import subprocess
import time
import json
import os

ext_dict = {'mp4':'video/mp4', 'mkv':'video/mp4', 'webm':'video/webm'}

class ChromecastPlayer(Gtk.Application):

    def __init__(self, uri):
        Gtk.Application.__init__(self,
                                 application_id='org.gnome.chromecast-player',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name("Chromecast Player")
        GLib.set_prgname('chromecast-player')
        self.connect("activate", self._on_activate, uri)
        self.cast = None
        self.get_chromecast_config()
        self.uri = None
        self.play_now = True if uri else False
        self.play_uri = []
        self.uri_working = False
        if uri and not isinstance(uri, (list, tuple)):
            self.uri = [uri]
        elif uri:
            self.uri = uri
        self.multiple_files = False
        self.loaded = False
        self.loc_file = None
        self.stop_worker = False
        self.is_playing = False
        self.is_paused = False
        self.is_idle = False
        self.is_disconnected = False
        self.playlist_counter = 0
        self.seeking = False
    
    def exit(self, *args):
        self.win.close()
        self.stop_worker = True
        self.quit()

    def _on_activate(self, app, uri):
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
        
        playlistButtonImage = Gtk.Image()
        playlistButtonImage.set_from_icon_name('view-media-playlist', Gtk.IconSize.BUTTON)

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
        
        self.play.add(playButtonImage)
        self.pause = Gtk.Button()
        
        self.pause.add(pauseButtonImage)
        self.stop = Gtk.Button()
        self.stop.add(stopButtonImage)
        
        self.prev = Gtk.Button()
        self.prev.add(prevButtonImage)
        self.next = Gtk.Button()
        self.next.add(nextButtonImage)

        refresh = Gtk.Button()
        refresh.add(refreshButtonImage)

        self.load = Gtk.Button()
        self.load.add(loadButtonImage)
        self.load.set_sensitive(False)

        self.playlist_button = Gtk.Button()
        self.playlist_button.add(playlistButtonImage)
        self.playlist_button.set_sensitive(False)

        self.disconnect = Gtk.Button()
        self.disconnect.add(disconnectButtonImage)

        self.volume = Gtk.VolumeButton()

        self.progressbar = Gtk.HScale()
        self.progressbar.set_margin_left(6)
        self.progressbar.set_margin_right(6)
        self.progressbar.set_draw_value(False)
        self.progressbar.set_range(0, 1)

        self.label = Gtk.Label(label='00:00/00:00')
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
                    if self.play_now:
                        #TODO
                        pass
            else:
                self.clients_combo.set_active(-1)
        else:
            self.clientstore.append([""])
            self.clients_combo.set_sensitive(False)
        

        
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_fixed_size(120, 20)
        self.clients_combo.pack_start(renderer_text, True)
        self.clients_combo.add_attribute(renderer_text, "text", 0)

        close = Gtk.Button("_Close", use_underline=True)
        close.get_style_context().add_class("destructive-action")

        hboxclient.pack_start(self.load, True, False, 2)
        hboxclient.pack_start(self.playlist_button, True, False, 2)
        hboxclient.pack_start(self.clients_combo, True, False, 2)
        hboxclient.pack_start(refresh, True, False, 2)
        hboxclient.pack_start(self.disconnect, True, False, 2)
        hboxclient.set_margin_left(30)

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

        hboxclose.pack_start(self.volume, False, False, 3)
        hboxclose.pack_end(close, False, False, 30)
        vboxall.set_margin_top(10)
        vboxall.pack_start(hboxprogress, True, False, 0)
        vboxall.pack_start(hboxbuttons, True, False, 10)
        vboxall.pack_start(hboxclose, False, False, 10)

        mainmenu = Gtk.Menu()
        filem = Gtk.MenuItem("Open")
        mainmenu.append(filem)

        self.streamm = Gtk.MenuItem("Open network stream")
        mainmenu.append(self.streamm)

        if not self.enable_web:
            self.streamm.set_sensitive(False)

        prefm = Gtk.MenuItem("Preferences")
        mainmenu.append(prefm)

        exit = Gtk.MenuItem("Close")

        mainmenu.append(exit)

        root_menu = Gtk.MenuItem('File')
        root_menu.set_submenu(mainmenu)

        menu_bar = Gtk.MenuBar()
        menu_bar.append(root_menu)

        vboxall.pack_start(menu_bar, False, False, 2)

        self.streamm.connect('activate', self._on_net_stream_clicked)
        self.play.connect("clicked", self._on_play_clicked)
        self.pause.connect("clicked", self._on_pause_clicked)
        self.stop.connect("clicked", self._on_stop_clicked)
        self.progressbar.connect("value_changed", self.slider_changed)
        self.clients_combo.connect("changed", self.combo_changed_clients)
        refresh.connect("clicked", self._on_refresh_clicked)
        self.load.connect("clicked", self._on_load_clicked)
        self.playlist_button.connect("clicked", self._on_playlist_clicked)
        self.disconnect.connect("clicked", self._on_disconnect_clicked)
        filem.connect('activate', self._on_file_clicked)
        close.connect("clicked", self.exit)
        prefm.connect('activate', self._on_preferences_clicked)
        exit.connect("activate", self.exit)
        self.win.connect("delete-event", self.exit) 

        self._worker_thread()
        GLib.timeout_add(500,self._worker_thread)
        self.win.show_all()
        self.add_window(self.win)


    def _on_preferences_clicked(self, *args):
        win = preferences.Preferences()
        win.run()
        self.get_chromecast_config()
        if not self.enable_web:
            self.streamm.set_sensitive(False)


    def _on_disconnect_clicked(self, *args):
        if self.cast:
            self.cast.quit_app()
            self.cast.disconnect()
        self.clients_combo.set_active(-1)
        self.play_uri = []


    def _on_file_clicked(self, *args):
        win = FileChooserWindow()
        ret = win.main()
        if ret and isinstance(ret, (list, tuple)):
            for u,i in enumerate(ret):
                self.multiple_files = True
                self.decode_local_uri(u)
                if i == 0:
                    self.loc_file = self.play_uri[-1]
        elif ret:
            self.multiple_files = False
            self.decode_local_uri(ret)
        self.load.set_sensitive(True)
        self.playlist_button.set_sensitive(True)


    def _on_play_clicked(self, *args):
        if self.cast and self.cast.status:
            if self.loaded:
                self.mc.stop()
                self.cast.wait()
                if self.play_uri[self.playlist_counter][1]:
                    subprocess.Popen(["stream2chromecast", "-devicename", self.cast.host, self.play_uri[self.playlist_counter][0]])
                else:
                    subprocess.Popen(["stream2chromecast", "-devicename", self.cast.host, "-playurl", self.play_uri[self.playlist_counter][0]])
                self.loaded = False
            if self.is_paused:
                self.mc.play()


    def _on_pause_clicked(self, *args):
        if self.cast:
            if self.is_playing:
                self.mc.pause()


    def _on_stop_clicked(self, *args):
        if self.cast:
            if self.is_playing or self.is_paused:
                self.mc.stop()
        self.play_uri = []


    def _on_net_stream_clicked(self, *args):
        win = NetworkStream()
        ret = win.main()
        thread = threading.Thread(target=self.get_network_uri, args=(ret,))
        thread.start()
        while self.uri_working:
            time.sleep(1)
        self.load.set_sensitive(True)
        self.playlist_button.set_sensitive(True)


    def _on_load_clicked(self, *args):
        while True:
            if not self.uri_working:
                break
            time.sleep(0.5)
        if self.multiple_files:
            self.multiple_files = False
            self.play_uri = [self.loc_file]
        else:
            self.play_uri = [self.play_uri[-1]]
        self.playlist_counter = 0
        self.play.set_sensitive(True)
        self.loaded = True
        self.load.set_sensitive(False)
        self.playlist_button.set_sensitive(False)


    def _on_playlist_clicked(self, *args):
        while True:
            if not self.uri_working:
                break
            time.sleep(0.5)
        self.load.set_sensitive(False)
        self.playlist_button.set_sensitive(False)


    def _on_refresh_clicked(self, *args):
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


    def get_chromecast_config(self):
        chromecast_config = preferences.get_config('chromecast_player')
        self.automatic_connect = chromecast_config['automatic_connect']
        self.enable_web = chromecast_config['enable_web']


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


    def slider_changed(self, *args):
        self.seeking = True
        widget = args[0]
        value = widget.get_value()
        if self.is_playing or self.is_paused and self.mc.supports_seek:
            dur = self.mc.status.duration
            curr = self.mc.status.current_time
            self.mc.seek(value*dur)
            widget.set_value(value)
            self.label.set_label("%02d:%02d/%02d:%02d"%(int(value/60), int(value%60), int(dur/60), int(dur%60)))
            GLib.timeout_add(500,self._seeker_thread, curr)
        else:
            return


    def _seeker_thread(self, curr):
        self.mc.update_status(blocking=True)
        curr2 = self.mc.status.current_time
        if curr == curr2:
            return True
        else:
            self.seeking = False
            return False


    def decode_local_uri(self, uri):
        while True:
            if not self.uri_working:
                break
            time.sleep(0.5)
        url = unquote(urlparse(uri).path)
        if os.path.exists(url):
            self.play_uri.append((url, True))


    def get_network_uri(self, url):
        self.uri_working = True
        try:
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
            else:
                url = dicti['url']
            self.play_uri.append((url, False))
            self.multiple_files = False
        except:
            pass
        self.uri_working = False


    def _worker_thread(self):
        if self.stop_worker:
            return False
        if self.cast and self.cast.status:
            self.disconnect.set_sensitive(True)
            try:
                self.mc.update_status(blocking=True)
            except:
                pass
            if self.mc.status.player_state == 'PLAYING' or (self.mc.status.player_state == 'BUFFERING' and self.mc.status.current_time != 0):
                self.is_playing = True
                self.is_paused = False
                self.is_idle = False
                self.is_disconnected = False
                if not self.seeking:
                    curr = self.mc.status.current_time
                    dur = self.mc.status.duration
                    self.progressbar.handler_block_by_func(self.slider_changed)
                    self.progressbar.set_value(curr/dur)
                    self.progressbar.handler_unblock_by_func(self.slider_changed)
                    self.label.set_label("%02d:%02d/%02d:%02d"%(int(curr/60), int(curr%60), int(dur/60), int(dur%60)))
                self.pause.set_sensitive(True)
                self.stop.set_sensitive(True)
                self.volume.set_sensitive(True)
                if self.mc.status.supports_skip_forward or (len(self.play_uri) > self.playlist_counter + 1):
                    self.next.set_sensitive(True)
                else:
                    self.next.set_sensitive(False)
                if self.mc.status.supports_skip_backward or (self.playlist_counter != 0):
                    self.prev.set_sensitive(True)
                else:
                    self.prev.set_sensitive(False)
                if not self.loaded:
                    self.play.set_sensitive(False)
                else:
                    self.play.set_sensitive(True)
            elif self.mc.status.player_state == 'PAUSED':
                self.is_playing = False
                self.is_paused = True
                self.is_idle = False
                self.is_disconnected = False
                self.pause.set_sensitive(False)
                self.play.set_sensitive(True)
                self.volume.set_sensitive(True)
                self.stop.set_sensitive(True)
                if self.mc.status.supports_skip_forward or (len(self.play_uri) > self.playlist_counter + 1):
                    self.next.set_sensitive(True)
                else:
                    self.next.set_sensitive(False)
                if self.mc.status.supports_skip_backward or (self.playlist_counter != 0):
                    self.prev.set_sensitive(True)
                else:
                    self.prev.set_sensitive(False)
            elif self.mc.status.player_state == 'IDLE':
                self.is_playing = False
                self.is_paused = False
                self.is_idle = True
                self.is_disconnected = False
                self.label.set_label("0:00/0:00")
                self.stop.set_sensitive(False)
                self.volume.set_sensitive(False)
                self.prev.set_sensitive(False)
                self.next.set_sensitive(False)
                self.progressbar.handler_block_by_func(self.slider_changed)
                self.progressbar.set_value(0.)
                self.progressbar.handler_unblock_by_func(self.slider_changed)
                self.pause.set_sensitive(False)
                if not self.loaded:
                    self.play.set_sensitive(False)
                else:
                    self.play.set_sensitive(True)

            else:
                self.is_playing = False
                self.is_paused = False
                self.is_idle = False
                self.is_disconnected = False
                self.label.set_label("0:00/0:00")
                self.stop.set_sensitive(False)
                self.pause.set_sensitive(False)
                self.volume.set_sensitive(False)
                self.prev.set_sensitive(False)
                self.next.set_sensitive(False)
                self.progressbar.handler_block_by_func(self.slider_changed)
                self.progressbar.set_value(0.)
                self.progressbar.handler_unblock_by_func(self.slider_changed)
                if not self.loaded:
                    self.play.set_sensitive(False)
                else:
                    self.play.set_sensitive(True)
        else:
            self.is_playing = False
            self.is_paused = False
            self.is_idle = False
            self.is_disconnected = True
            self.disconnect.set_sensitive(False)
            self.label.set_label("00:00/00:00")
            self.pause.set_sensitive(False)
            self.volume.set_sensitive(False)
            self.stop.set_sensitive(False)
            self.prev.set_sensitive(False)
            self.next.set_sensitive(False)
            self.progressbar.handler_block_by_func(self.slider_changed)
            self.progressbar.set_value(0.)
            self.progressbar.handler_unblock_by_func(self.slider_changed)
            if self.loaded:
                self.play.set_sensitive(True)
            else:
                self.play.set_sensitive(False)
        return True 


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
        filter_text.set_name("Video/Audio files")
        filter_text.add_mime_type("video/*")
        filter_text.add_mime_type("audio/*")
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
        self.win.set_size_request(300, 10)
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
        

