#!/usr/bin/python3

from gi import require_version
require_version("Gtk", "3.0")
require_version("Notify", "0.7")
from gi.repository import Gtk, Gdk, Gio, GLib, Notify
from urllib.parse import urlparse, unquote, quote_plus
import pychromecast as pyc
import preferences
import threading
import subprocess
import mimetypes
import server as local_server
import time
import json
import http.server
import os
import socket

FFMPEG = 'ffmpeg -i "%s" -strict -2 -preset ultrafast -f mp4 -frag_duration 3000 -b:v 2000k -loglevel error %s -'
AVCONV = 'avconv -i "%s" -strict -2 -preset ultrafast -f mp4 -frag_duration 3000 -b:v 2000k -loglevel error %s -'

supported_formats = {'mp4':('video/mp4', 0), 'webm':('video/webm', 1), 'ogg':('audio/ogg', 2), 'flac':("audio/flac", 1.5),'flac':("audio/x-flac", 1.6), 'mp3':('audio/mpeg', 3), 'wav':('audio/wav', 4)}

class ChromecastPlayer(Gtk.Application):

    def __init__(self, uri, show_gui=True):
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
        self.serverthread = None
        self.local_port = 0
        self.show_gui = show_gui
        self.transcode_options = None
        if uri and not isinstance(uri, (list, tuple)):
            self.uri = [uri]
        elif uri:
            self.uri = uri
        self.loaded = False
        self.loc_file = None
        self.stop_worker = False
        self.is_playing = False
        self.is_paused = False
        self.is_idle = False
        self.is_disconnected = False
        self.playlist_counter = 0
        self.seeking = False
        self.overwrite = False
        self.continue_playing = False
        self.volume_changing = False


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
        refresh.set_tooltip_text("Refresh chromecast list")

        self.disconnect = Gtk.Button()
        self.disconnect.add(disconnectButtonImage)
        self.disconnect.set_tooltip_text("Disconnect from chromecast")

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
                        for uri in self.uri:
                            if self.decode_local_uri(uri): 
                                continue
                            else:
                                self.get_network_uri(uri)
                        if self.play_uri:
                            self._on_play_clicked()
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
        self.volume.connect("value_changed", self.volume_changed)
        self.clients_combo.connect("changed", self.combo_changed_clients)
        refresh.connect("clicked", self._on_refresh_clicked)
        self.next.connect("clicked", self._on_next_clicked)
        self.prev.connect("clicked", self._on_prev_clicked)
        self.disconnect.connect("clicked", self._on_disconnect_clicked)
        filem.connect('activate', self._on_file_clicked)
        close.connect("clicked", self.exit)
        prefm.connect('activate', self._on_preferences_clicked)
        exit.connect("activate", self.exit)
        self.win.connect("delete-event", self.exit) 

        self._worker_thread()
        GLib.timeout_add(500,self._worker_thread)
        if self.show_gui:
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


    def _on_play_clicked(self, *args):
        if self.cast and self.cast.status:
            self.overwrite = False
            if self.is_paused:
                self.mc.play()
            else:
                self.play_media()


    def _on_pause_clicked(self, *args):
        if self.cast:
            if self.is_playing:
                self.mc.pause()


    def _on_stop_clicked(self, *args):
        if self.cast:
            if self.is_playing or self.is_paused:
                self.mc.stop()
                if self.serverthread:
                    while self.serverthread.isAlive():
                        time.sleep(0.5)
        self.playlist_counter = 0
        self.play_uri = []
        self.continue_playing = False


    def _on_file_clicked(self, *args):
        win = FileChooserWindow()
        ret = win.main()
        playlist = self.play_uri.copy()
        if ret:
            while True:
                if not self.uri_working:
                    break
            if ret[1] == 1:
                self.play_uri = []
                self.playlist_counter = 0
                for i,u in enumerate(ret[0]):
                    self.decode_local_uri(u)
                self.mc.stop()
                if self.play_uri:
                    self._on_play_clicked()
            else:
                if self.overwrite:
                    self.play_uri = []
                    self.playlist_counter = 0
                for i, u in enumerate(ret[0]):
                    self.decode_local_uri(u)
                if self.overwrite or not playlist and self.play_uri:
                    self._on_play_clicked()


    def _on_net_stream_clicked(self, *args):
        win = NetworkStream()
        ret = win.main()
        playlist = self.play_uri.copy()
        if ret:
            while True:
                if not self.uri_working:
                    break
            if ret[1] == 1:
                self.play_uri = []
                self.playlist_counter = 0
                thread = threading.Thread(target=self.get_network_uri, args=(ret[0],))
                thread.start()
                while self.uri_working:
                    time.sleep(1)
                if self.play_uri:
                    self.mc.stop()
                    self._on_play_clicked()
            else:
                thread = threading.Thread(target=self.get_network_uri, args=(ret[0],))
                thread.start()
                while self.uri_working:
                    time.sleep(1)
                if not playlist and self.play_uri:
                    self._on_play_clicked()


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
        if not chromecast_config['enable_transcoding']:
            self.transcoder = None
            self.probe = None
        self.transcoder = chromecast_config['enable_transcoding']
        self.preferred_transcoder = chromecast_config["preferred_transcoder"]
        self.local_port = chromecast_config["local_port"]
        self.transcoder, self.probe = get_transcoder_cmds(preferred_transcoder=self.preferred_transcoder)


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

    def _on_next_clicked(self, *args):
        self.play.set_sensitive(False)
        if self.cast and self.cast.status:
            if self.continue_playing and (self.playlist_counter + 1) < len(self.play_uri):
                self.playlist_counter += 1
                self.play_media()
            elif (self.playlist_counter + 1) >= len(self.play_uri):
                self.continue_playing = False
                self.overwrite = True
                self.playlist_counter = 0
                self.mc.stop()
                if self.serverthread:
                    while self.serverthread.isAlive():
                        time.sleep(0.5)                


    def _on_prev_clicked(self, *args):
        self.play.set_sensitive(False)
        if self.cast and self.cast.status:
            if self.playlist_counter != 0:
                self.playlist_counter += -1
                self.play_media()


    def play_media(self):
        self.mc.stop()
        self.cast.wait()
        if self.serverthread:
            while self.serverthread.isAlive():
                time.sleep(0.5)
        while not self.is_idle:
            time.sleep(0.5)
        if self.play_uri[self.playlist_counter][1]:
            url = self.local_url(self.play_uri[self.playlist_counter][0], self.play_uri[self.playlist_counter][3], self.transcoder, self.transcode_options, self.local_port)
            self.mc.play_media(url, self.play_uri[self.playlist_counter][2])
        else:
            self.mc.play_media(self.play_uri[self.playlist_counter][0], self.play_uri[self.playlist_counter][2])


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

    def volume_changed(self, *args):
        self.volume_changing = True
        widget = args[0]
        value = widget.get_value()
        if self.is_playing or self.is_paused:
            self.cast.set_volume(value)
        GLib.timeout_add(500,self._volume_thread, value)


    def _volume_thread(self, curr):
        st = time.time()
        self.mc.update_status(blocking=True)
        curr2 = self.mc.status.volume_level
        if curr != curr2:
            return True
        elif time.time()-st < 2 or curr == curr2:
            self.volume_changing = False
            return False


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
        mime = get_mimetype(url, self.probe)
        transcode = False
        if self.transcoder:
            transcode = True
        for k in supported_formats.keys():
            if mime == supported_formats[k][0]:
                transcode = False
        if os.path.exists(url):
            self.play_uri.append((url, True, mime, transcode and self.transcoder))
            return True
        else:
            return False

    def get_network_uri(self, url):
        self.uri_working = True
        try:
            proc = subprocess.Popen(['youtube-dl', '-j', url], stdout=subprocess.PIPE)
            ret = proc.communicate()[0]
            dicti = json.loads(ret.decode('utf-8'))
            if 'formats' in list(dicti.keys()):
                exts = []
                for fs in dicti['formats']:
                    ind = 100
                    if not fs['ext'] in exts:
                        exts.append(fs['ext'])
                exte = 'mp4'
                mime = 'video/mp4'
                for ext in exts:
                    if ext in supported_formats.keys() and ind > supported_formats[ext][1]:
                        ind = supported_formats[ext][1]
                        mime = supported_formats[ext][0]
                        exte = ext
                proc = subprocess.Popen(['youtube-dl', '-f', exte, '-g', url], stdout=subprocess.PIPE)
                ret = proc.communicate()[0].decode('utf-8')
                url = ret
            else:
                url = dicti['url']
                mime = supported_formats[dicti['ext']][0]
            if url:
                self.play_uri.append((url, False, mime, False))
        except Exception as e:
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
                self.continue_playing = True
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
                self.play.set_sensitive(False)
                if self.mc.status.title:
                    self.win.set_title()    
                if not self.volume_changing:
                    self.volume.handler_block_by_func(self.volume_changed)
                    self.volume.set_value(self.mc.status.volume_level)
                    self.volume.handler_unblock_by_func(self.volume_changed)
                if self.mc.status.supports_skip_forward or (len(self.play_uri) > self.playlist_counter + 1):
                    self.next.set_sensitive(True)
                else:
                    self.next.set_sensitive(False)
                if self.mc.status.supports_skip_backward or (self.playlist_counter != 0):
                    self.prev.set_sensitive(True)
                else:
                    self.prev.set_sensitive(False)
            elif self.mc.status.player_state == 'PAUSED':
                self.is_playing = False
                self.is_paused = True
                self.is_idle = False
                self.is_disconnected = False
                self.pause.set_sensitive(False)
                self.play.set_sensitive(True)
                self.volume.set_sensitive(True)
                if not self.volume_changing:
                    self.volume.handler_block_by_func(self.volume_changed)
                    self.volume.set_value(self.mc.status.volume_level)
                    self.volume.handler_unblock_by_func(self.volume_changed)
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
                self.volume.handler_block_by_func(self.volume_changed)
                self.volume.set_value(0)
                self.volume.handler_unblock_by_func(self.volume_changed)
                self.prev.set_sensitive(False)
                self.next.set_sensitive(False)
                self.progressbar.handler_block_by_func(self.slider_changed)
                self.progressbar.set_value(0.)
                self.progressbar.handler_unblock_by_func(self.slider_changed)
                self.pause.set_sensitive(False)
                self.win.set_title("Chromecast Player")
                if self.continue_playing and self.mc.status.idle_reason == 'FINISHED':
                    print("test")
                    self._on_next_clicked()
                if self.play_uri and not (self.continue_playing and self.mc.status.idle_reason == 'FINISHED'):
                    self.play.set_sensitive(True)
            else:
                self.is_playing = False
                self.is_paused = False
                self.is_idle = False
                self.is_disconnected = False
                self.win.set_title("Chromecast Player")
                self.label.set_label("0:00/0:00")
                self.stop.set_sensitive(False)
                self.pause.set_sensitive(False)
                self.volume.set_sensitive(False)
                self.volume.handler_block_by_func(self.volume_changed)
                self.volume.set_value(0)
                self.volume.handler_unblock_by_func(self.volume_changed)
                self.prev.set_sensitive(False)
                self.next.set_sensitive(False)
                self.progressbar.handler_block_by_func(self.slider_changed)
                self.progressbar.set_value(0.)
                self.progressbar.handler_unblock_by_func(self.slider_changed)
                if self.play_uri and not self.continue_playing:
                    self.play.set_sensitive(True)
                else:
                    self.play.set_sensitive(False)
        else:
            self.continue_playing = False
            self.is_playing = False
            self.is_paused = False
            self.is_idle = False
            self.is_disconnected = True
            self.win.set_title("Chromecast Player")
            self.disconnect.set_sensitive(False)
            self.label.set_label("00:00/00:00")
            self.pause.set_sensitive(False)
            self.volume.set_sensitive(False)
            self.volume.handler_block_by_func(self.volume_changed)
            self.volume.set_value(0)
            self.volume.handler_unblock_by_func(self.volume_changed)
            self.stop.set_sensitive(False)
            self.prev.set_sensitive(False)
            self.next.set_sensitive(False)
            self.progressbar.handler_block_by_func(self.slider_changed)
            self.progressbar.set_value(0.)
            self.progressbar.handler_unblock_by_func(self.slider_changed)
            self.play.set_sensitive(False)
        return True 


    def local_url(self, filename, transcode=False, transcoder=None, transcode_options=None, server_port=None):
        """ play a local file on the chromecast """

        if os.path.isfile(filename):
            filename = os.path.abspath(filename)
        else:
            return None

        mimetype = get_mimetype(filename, self.probe)
        webserver_ip =[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
        
        req_handler = local_server.RequestHandler

        if transcode:
            if transcoder == "ffmpeg":  
                req_handler = local_server.TranscodingRequestHandler
                req_handler.transcoder_command = FFMPEG
            elif transcoder == "avconv":   
                req_handler = local_server.TranscodingRequestHandler
                req_handler.transcoder_command = AVCONV
            
            if transcode_options is not None:    
                req_handler.transcode_options = transcode_options

        # create a webserver to handle a single request on a free port or a specific port if passed in the parameter   
        port = 0    
        if server_port is not None:
            port = int(server_port)
            
        server = http.server.HTTPServer((webserver_ip, port), req_handler)
        self.serverthread = threading.Thread(target=server.handle_request)
        self.serverthread.start()    

        url = "http://%s:%s%s" % (webserver_ip, str(server.server_port), quote_plus(filename, "/"))
        
        return url


    def get_active_chromecasts(self):
        casts = list(pyc.get_chromecasts_as_dict().keys())
        self.chromecasts = list(casts)
        return self.chromecasts


class FileChooserWindow(Gtk.Window):

    def __init__(self):
        self.win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.but = 0

    def main(self):
        
        dialog = Gtk.FileChooserDialog("Please choose a file", self.win,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))
        self.button1 = dialog.add_button('Add to playlist', Gtk.ResponseType.OK)
        self.button2 = dialog.add_button('Play now', Gtk.ResponseType.OK)
        self.button1.connect("clicked", self._button_clicked)
        self.button2.connect("clicked", self._button_clicked)
        dialog.set_select_multiple(True)
        self.add_filters(dialog)
        ret = None
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            ret = (dialog.get_uris(), self.but)
        dialog.destroy()
        return ret

    def _button_clicked(self, *args):
        if args[0] == self.button1:
            self.but = 2
        else:
            self.but = 1
            
        
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
                   (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
             )
        self.button1 = self.win.add_button('Add to playlist', Gtk.ResponseType.OK)
        self.button2 = self.win.add_button('Play now', Gtk.ResponseType.OK)
        self.button1.connect("clicked", self._button_clicked)
        self.button2.connect("clicked", self._button_clicked)
        self.ret = None

    def _button_clicked(self, *args):
        if args[0] == self.button1:
            self.but = 2
        else:
            self.but = 1

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
        if self.ret:
            return (self.ret, self.but)
        else:
            return None


def get_mimetype(filename, ffprobe_cmd=None):
    """ find the container format of the file """
    # default value
    mimetype = "video/mp4"

    # guess based on filename extension
    guess = mimetypes.guess_type(filename)[0]
    if guess is not None:
        if guess.lower().startswith("video/") or guess.lower().startswith("audio/"):
            mimetype = guess

    # use the OS file command...
    try:
        file_cmd = 'file --mime-type -b "%s"' % filename
        file_mimetype = subprocess.check_output(file_cmd, shell=True).strip().lower().decode('utf-8')
        if file_mimetype.startswith("video/") or file_mimetype.startswith("audio/"):
            mimetype = file_mimetype
            return mimetype
    except:
        pass

    # use ffmpeg/avconv if installed
    if ffprobe_cmd is None:
        return mimetype
    
    # ffmpeg/avconv is installed
    has_video = False
    has_audio = False
    format_name = None
    
    ffprobe_cmd = '%s -show_streams -show_format "%s"' % (ffprobe_cmd, filename)
    ffmpeg_process = subprocess.Popen(ffprobe_cmd, stdout=subprocess.PIPE, shell=True)
    for line in ffmpeg_process.stdout:
        l = line.decode('utf-8')
        if l.startswith("codec_type=audio"):
            has_audio = True
        elif l.startswith("codec_type=video"):
            has_video = True    
        elif l.startswith("format_name="):
            name, value = l.split("=")
            format_name = value.strip().lower().split(",")

    # use the default if it isn't possible to identify the format type
    if format_name is None:
        return mimetype

    if has_video:
        mimetype = "video/"
    else:
        mimetype = "audio/"
        
    if "mp4" in format_name:
        mimetype += "mp4"
    elif "webm" in format_name:
        mimetype += "webm"
    elif "ogg" in format_name:
        mimetype += "ogg"
    elif "mp3" in format_name:
        mimetype = "audio/mpeg"
    elif "wav" in format_name:
        mimetype = "audio/wav"
    elif "flac" in format_name:
        mimetype = "audio/flac"
    else:   
        mimetype += "mp4"

    return mimetype


def get_transcoder_cmds(preferred_transcoder=None):
    """ establish which transcoder utility to use depending on what is installed """
    probe_cmd = None
    transcoder_cmd = None
    
    ffmpeg_installed = is_transcoder_installed("ffmpeg")
    avconv_installed = is_transcoder_installed("avconv")  
    
    # if anything other than avconv is preferred, try to use ffmpeg otherwise use avconv    
    if preferred_transcoder != "avconv":
        if ffmpeg_installed:
            transcoder_cmd = "ffmpeg"
            probe_cmd = "ffprobe"
        elif avconv_installed:
            transcoder_cmd = "avconv"
            probe_cmd = "avprobe"
    
    # otherwise, avconv is preferred, so try to use avconv, followed by ffmpeg  
    else:
        if avconv_installed:
            transcoder_cmd = "avconv"
            probe_cmd = "avprobe"
        elif ffmpeg_installed:
            transcoder_cmd = "ffmpeg"
            probe_cmd = "ffprobe"
            
    return transcoder_cmd, probe_cmd


def is_transcoder_installed(transcoder_application):
    """ check for an installation of either ffmpeg or avconv """
    try:
        subprocess.check_output([transcoder_application, "-version"])
        return True
    except OSError:
        return False


if __name__ == '__main__':
    import sys
    win = ChromecastPlayer(sys.argv[1:])
    win.run()
