#!/usr/bin/python3

"""
stream2chromecast.py: Chromecast media streamer for Linux
author: wa4557 - https://github.com/wa4557/chromecast-player
version: 0.1
"""

# Copyright (C) 2016 wa4557
#
# This file is part of chromecast-player.
#
# chromecast-player is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# chromecast-player is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with chromecast-player.  If not, see <http://www.gnu.org/licenses/>.


from gi import require_version
require_version("Gtk", "3.0")
require_version("Notify", "0.7")
from gi.repository import Gtk, Gdk, Gio, GLib, Notify
from urllib.parse import quote_plus
import pychromecast as pyc
import preferences
import helpers
import playlist_manager
from stream_select import FileChooserWindow, NetworkStream
import threading
import re
import local_server
import time
import http.server
import os
import socket

FFMPEG_VIDEO = 'ffmpeg -i "%s" -strict -2 -preset ultrafast -f mp4 -frag_duration 3000 -b:v 2000k -loglevel error %s -'
AVCONV_VIDEO = 'avconv -i "%s" -strict -2 -preset ultrafast -f mp4 -frag_duration 3000 -b:v 2000k -loglevel error %s -'

FFMPEG_AUDIO = 'ffmpeg -i "%s" -strict -2 -preset ultrafast -codec:a aac -frag_duration 3000 -b:v 2000k -loglevel error %s -'
AVCONV_AUDIO = 'avconv -i "%s" -strict -2 -preset ultrafast -codec:a aac -frag_duration 3000 -b:v 2000k -loglevel error %s -'

class ChromecastPlayer(Gtk.Application):

    def __init__(self, uri, show_gui=True):
        Gtk.Application.__init__(self,
                                 application_id='org.gnome.chromecast-player',
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        GLib.set_application_name("Chromecast Player")
        GLib.set_prgname('chromecast-player')
        self.connect("activate", self._on_activate, uri)
        self.cast = None
        self.mc = None
        self.get_chromecast_config()
        self.uri = None
        self.play_now = True if uri else False
        self.play_uri = []
        self.serverthread = None
        self.subtitlethread = None
        self.local_port = 0
        self.show_gui = show_gui
        self.imagethread = None
        self.transcode_options = None
        self.playlist_manager = None
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
        if self.playlist_manager:
            if self.playlist_manager.win.is_visible():
                self.playlist_manager.win.close()
        self.win.close()
        self.stop_worker = True
        self.quit()


    def _on_activate(self, app, uri):
        self.win = Gtk.ApplicationWindow(Gtk.WindowType.TOPLEVEL, application=app)
        self.win.set_icon_name('chromecast-player')
        self.win.set_position(Gtk.WindowPosition.CENTER)
        
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
        refresh.set_tooltip_text("Refresh chromecast list")

        self.playlist = Gtk.Button()
        self.playlist.add(playlistButtonImage)
        self.playlist.set_tooltip_text("Manage playlist")

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
                            u = helpers.decode_local_uri(uri, self.transcoder, self.probe, self.preferred_transcoder)
                            if u: 
                                self.play_uri.append(u)
                            else:
                                n = helpers.decode_network_uri(uri)
                                if n:
                                    self.play_uri.append(n)
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

        hboxclient.pack_start(self.playlist, True, False, 2)
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
        self.progressbar.connect("value_changed", self._slider_changed)
        self.volume.connect("value_changed", self._volume_changed)
        self.clients_combo.connect("changed", self._combo_changed_clients)
        self.playlist.connect("clicked", self._on_playlist_clicked)
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
            if self.playlist_manager:
                self.playlist_manager.streamm.set_sensitive(False)
                self.playlist_manager.netbutton.set_sensitive(False)
        else:
            self.streamm.set_sensitive(True)
            if self.playlist_manager:
                self.playlist_manager.streamm.set_sensitive(True)
                self.playlist_manager.netbutton.set_sensitive(True)
        if self.playlist_manager:
            self.playlist_manager.transcoder = self.transcoder
            self.playlist_manager.probe = self.probe
            self.playlist_manager.preferred_transcoder = self.preferred_transcoder


    def _on_disconnect_clicked(self, *args):
        if self.cast:
            self.cast.quit_app()
            self.cast.disconnect()
        self.clients_combo.set_active(-1)
        self.play_uri = []
        if self.playlist_manager:
            self.playlist_manager.check_uris(self.play_uri)


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
        self.playlist_counter = 0
        self.play_uri = []
        if self.playlist_manager:
            self.playlist_manager.check_uris(self.play_uri)
        self.continue_playing = False


    def _on_file_clicked(self, *args):
        win = FileChooserWindow()
        ret = win.main()
        playlist = self.play_uri.copy()
        if ret:
            if ret[1] == 1:
                self.play_uri = []
                self.playlist_counter = 0
                for i,u in enumerate(ret[0]):
                    self.play_uri.append(helpers.decode_local_uri(u, self.transcoder, self.probe, self.preferred_transcoder))
                if self.mc:
                    self.mc.stop()
                if self.play_uri:
                    self._on_play_clicked()
            else:
                if self.overwrite:
                    self.play_uri = []
                    self.playlist_counter = 0
                for i, u in enumerate(ret[0]):
                    self.play_uri.append(helpers.decode_local_uri(u, self.transcoder, self.probe, self.preferred_transcoder))
                if self.overwrite or not playlist and self.play_uri:
                    self._on_play_clicked()
            if self.playlist_manager:
                self.playlist_manager.check_uris(self.play_uri)


    def _on_net_stream_clicked(self, *args):
        win = NetworkStream()
        ret = win.main()
        playlist = self.play_uri.copy()
        if ret:
            if ret[1] == 1:
                self.play_uri = []
                self.playlist_counter = 0
                n = helpers.decode_network_uri(ret[0])
                if n:
                    self.play_uri.append(n)
                if self.play_uri and self.mc:
                    self.mc.stop()
                    self._on_play_clicked()
            else:
                n = helpers.decode_network_uri(ret[0])
                if n:
                    self.play_uri.append(n)
                if not playlist and self.play_uri:
                    self._on_play_clicked()
            if self.playlist_manager:
                self.playlist_manager.check_uris(self.play_uri)


    def _on_refresh_clicked(self, *args):
        self.clients_combo.handler_block_by_func(self._combo_changed_clients)
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
        self.clients_combo.handler_unblock_by_func(self._combo_changed_clients)    


    def _on_playlist_clicked(self, *args):
        counter = self.playlist_counter if self.is_playing or self.is_paused else None
        self.playlist_manager = playlist_manager.PlaylistManager(self.play_uri, self.enable_web, self.transcoder, self.probe, self.preferred_transcoder, counter)
        self.playlist_manager.main()
        GLib.timeout_add(500,self._playlist_watcher)


    def _playlist_watcher(self):
        if not self.playlist_manager.win.is_visible():
            self.playlist_manager = None
            return False
        if self.playlist_manager.playlist_changed:
            self.play_uri = self.playlist_manager.play_uri[:]
            self.playlist_manager.check_uris(self.play_uri)
            self.playlist_manager.playlist_changed = False
            if self.play_uri and self.playlist_manager.play_now:
                self.playlist_counter = 0
                self.playlist_manager.play_now = False
                if self.mc:
                    self.mc.stop()
                    self._on_play_clicked()
        if self.playlist_manager.number_clicked:
            self.playlist_counter += self.playlist_manager.number_clicked
            self.playlist_manager.playlist_counter = self.playlist_counter
            self.playlist_manager.number_clicked = 0
        elif self.playlist_manager.sorted_index is not None:
            self.playlist_counter = self.playlist_manager.sorted_index
            self.playlist_manager.playlist_counter = self.playlist_counter
            self.playlist_manager.sorted_index = None
        else:
            for row in self.playlist_manager.store:
                row[0] = None
            if self.playlist_manager.show_image and self.mc:
                if self.playlist_manager.playlist_counter is not None:
                    self.playlist_manager.store[self.playlist_manager.playlist_counter][0] = self.playlist_manager.playimage
        if self.playlist_manager.double_clicked:
            self.playlist_counter = self.playlist_manager.double_clicked_index
            if self.mc:
                self._on_play_clicked()
                self.playlist_manager.show_image = True
            self.playlist_manager.double_clicked = False
        return True


    def _combo_changed_clients(self, widget):
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
        if self.playlist_manager:
            self.playlist_manager.show_image = True
        if self.cast and self.cast.status:
            if self.continue_playing and (self.playlist_counter + 1) < len(self.play_uri):
                self.playlist_counter += 1
                self.play_media()
            elif (self.playlist_counter + 1) >= len(self.play_uri):
                self.continue_playing = False
                self.overwrite = True
                self.playlist_counter = 0
                self.mc.stop()


    def _on_prev_clicked(self, *args):
        self.play.set_sensitive(False)
        if self.cast and self.cast.status:
            if self.playlist_counter != 0:
                self.playlist_counter += -1
                self.play_media()


    def _slider_changed(self, *args):
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


    def _volume_changed(self, *args):
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


    def _worker_thread(self):
        if self.stop_worker:
            return False
        try:
            if self.play_uri:
                self.playlist.set_sensitive(True)
            else:
                self.playlist.set_sensitive(False)
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
                        self.progressbar.handler_block_by_func(self._slider_changed)
                        if dur and curr:
                            self.progressbar.set_value(curr/dur)
                        self.progressbar.handler_unblock_by_func(self._slider_changed)
                        self.label.set_label("%02d:%02d/%02d:%02d"%(int(curr/60), int(curr%60), int(dur/60), int(dur%60)))
                    self.pause.set_sensitive(True)
                    self.stop.set_sensitive(True)
                    self.volume.set_sensitive(True)
                    self.play.set_sensitive(False)
                    if self.mc.status.title:
                        self.win.set_title(self.mc.status.title)    
                    if not self.volume_changing:
                        self.volume.handler_block_by_func(self._volume_changed)
                        self.volume.set_value(self.mc.status.volume_level)
                        self.volume.handler_unblock_by_func(self._volume_changed)
                    if self.mc.status.supports_skip_forward or (len(self.play_uri) > self.playlist_counter + 1):
                        self.next.set_sensitive(True)
                    else:
                        self.next.set_sensitive(False)
                    if self.play_uri and (self.mc.status.supports_skip_backward or (self.playlist_counter != 0)):
                        self.prev.set_sensitive(True)
                    else:
                        self.prev.set_sensitive(False)
                    if self.playlist_manager:
                        self.playlist_manager.playlist_counter = self.playlist_counter
                elif self.mc.status.player_state == 'PAUSED':
                    self.is_playing = False
                    self.is_paused = True
                    self.is_idle = False
                    self.is_disconnected = False
                    self.pause.set_sensitive(False)
                    self.play.set_sensitive(True)
                    self.volume.set_sensitive(True)
                    if self.mc.status.title:
                        self.win.set_title(self.mc.status.title)
                    if not self.volume_changing:
                        self.volume.handler_block_by_func(self._volume_changed)
                        self.volume.set_value(self.mc.status.volume_level)
                        self.volume.handler_unblock_by_func(self._volume_changed)
                    self.stop.set_sensitive(True)
                    if self.mc.status.supports_skip_forward or (len(self.play_uri) > self.playlist_counter + 1):
                        self.next.set_sensitive(True)
                    else:
                        self.next.set_sensitive(False)
                    if self.play_uri and (self.mc.status.supports_skip_backward or (self.playlist_counter != 0)):
                        self.prev.set_sensitive(True)
                    else:
                        self.prev.set_sensitive(False)
                    if self.playlist_manager:
                        self.playlist_manager.playlist_counter = self.playlist_counter
                elif self.mc.status.player_state == 'IDLE':
                    self.is_playing = False
                    self.is_paused = False
                    self.is_idle = True
                    self.is_disconnected = False
                    self.label.set_label("0:00/0:00")
                    self.stop.set_sensitive(False)
                    self.volume.set_sensitive(False)
                    self.volume.handler_block_by_func(self._volume_changed)
                    self.volume.set_value(0)
                    self.volume.handler_unblock_by_func(self._volume_changed)
                    self.prev.set_sensitive(False)
                    self.next.set_sensitive(False)
                    self.progressbar.handler_block_by_func(self._slider_changed)
                    self.progressbar.set_value(0.)
                    self.progressbar.handler_unblock_by_func(self._slider_changed)
                    self.pause.set_sensitive(False)
                    self.win.set_title("Chromecast Player")
                    if self.continue_playing and self.mc.status.idle_reason == 'FINISHED':
                        self._on_next_clicked()
                    if self.play_uri and not (self.continue_playing and self.mc.status.idle_reason == 'FINISHED'):
                        self.play.set_sensitive(True)
                    if self.playlist_manager:
                        self.playlist_manager.playlist_counter = None
                        self.playlist_manager.show_image = True
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
                    self.volume.handler_block_by_func(self._volume_changed)
                    self.volume.set_value(0)
                    self.volume.handler_unblock_by_func(self._volume_changed)
                    self.prev.set_sensitive(False)
                    self.next.set_sensitive(False)
                    self.progressbar.handler_block_by_func(self._slider_changed)
                    self.progressbar.set_value(0.)
                    self.progressbar.handler_unblock_by_func(self._slider_changed)
                    if self.play_uri and not self.continue_playing:
                        self.play.set_sensitive(True)
                    else:
                        self.play.set_sensitive(False)
                    if self.playlist_manager:
                        self.playlist_manager.playlist_counter = None
                        self.playlist_manager.show_image = True
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
                self.volume.handler_block_by_func(self._volume_changed)
                self.volume.set_value(0)
                self.volume.handler_unblock_by_func(self._volume_changed)
                self.stop.set_sensitive(False)
                self.prev.set_sensitive(False)
                self.next.set_sensitive(False)
                self.progressbar.handler_block_by_func(self._slider_changed)
                self.progressbar.set_value(0.)
                self.progressbar.handler_unblock_by_func(self._slider_changed)
                self.play.set_sensitive(False)
                if self.playlist_manager:
                    self.playlist_manager.playlist_counter = None
                    self.playlist_manager.show_image = True
            return True
        except:
            return True


    def get_chromecast_config(self):
        chromecast_config = preferences.get_config('chromecast_player')
        self.automatic_connect = chromecast_config['automatic_connect']
        self.enable_web = chromecast_config['enable_web']
        if not chromecast_config['enable_transcoding']:
            self.transcoder = None
            self.probe = None
        self.preferred_transcoder = chromecast_config["preferred_transcoder"]
        self.local_port = chromecast_config["local_port"] if chromecast_config["local_port"] else None
        self.transcoder, self.probe = helpers.get_transcoder_cmds(preferred_transcoder=self.preferred_transcoder)
        self.transcoder = chromecast_config['enable_transcoding']


    def play_media(self):
        if self.play_uri[self.playlist_counter][0] is None:
            return
        self.mc.stop()
        self.cast.wait()
        if self.play_uri[self.playlist_counter][1]:
            url = self.local_url(self.play_uri[self.playlist_counter][0], self.play_uri[self.playlist_counter][3], self.transcoder, self.transcode_options, self.local_port)
            thumb = self.play_uri[self.playlist_counter][5]
            image_url = None
            if thumb:
                image_url = self.local_thumb(thumb, self.play_uri[self.playlist_counter][6])
            self.mc.play_media(url, self.play_uri[self.playlist_counter][2], metadata=self.play_uri[self.playlist_counter][4], thumb=image_url)
        else:
            self.mc.play_media(self.play_uri[self.playlist_counter][0], self.play_uri[self.playlist_counter][2])


    def connect_to_chromecast(self, name):
        self.cast = pyc.get_chromecast(friendly_name=name)
        if self.cast:
            self.cast.wait()
            self.mc = self.cast.media_controller
            self.mc.app_id = 'FE51E599'
            time.sleep(0.2)
            try:
                self.check_already_playing()
            except:
                pass


    def check_already_playing(self):
        self.mc.update_status()
        if self.mc.status.player_state == 'PLAYING' or self.mc.status.player_state == 'PAUSED' or (self.mc.status.player_state == 'BUFFERING' and self.mc.status.current_time != 0):
            metadata = {}
            try:
                metadata['title'] = self.mc.status.title
            except:
                pass
            try:
                metadata['albumName'] = self.mc.status.album_name
            except:
                pass
            try:
                metadata['artist'] = self.mc.status.artist
            except:
                pass
            try:
                metadata['composer'] = self.mc.status.composer
            except:
                pass
            try:
                metadata['trackNumber'] = self.mc.status.track
            except:
                pass
            try:
                metadata['discNumber'] = self.mc.status.cd
            except:
                pass
            try:
                metadata['albumArtist'] = self.mc.status.album_artist
            except:
                pass
            self.play_uri.append([None, False, self.mc.status.content_type, False, metadata, None, None])

    def local_url(self, filename, transcode=False, transcoder=None, transcode_options=None, server_port=None):
        """ play a local file on the chromecast """

        if os.path.isfile(filename):
            filename = os.path.abspath(filename)
        else:
            return None

        mimetype = helpers.get_mimetype(filename, self.probe)
        webserver_ip =[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
        
        req_handler = local_server.RequestHandler
        req_handler.content_type = mimetype
        if transcode:
            req_handler = local_server.TranscodingRequestHandler
            if transcoder == "ffmpeg":
                if mimetype.startswith("audio"):
                    req_handler.transcoder_command = FFMPEG_AUDIO
                else:
                    req_handler.transcoder_command = FFMPEG_VIDEO
            elif transcoder == "avconv":   
                if mimetype.startswith("audio"):
                    req_handler.transcoder_command = AVCONV_AUDIO
                else:
                    req_handler.transcoder_command = AVCONV_VIDEO
            else:
                return
            if mimetype.startswith("audio"):
                req_handler.content_type = "audio/mp4"
            else:
                req_handler.content_type = "video/mp4"
            if transcode_options is not None:    
                req_handler.transcode_options = transcode_options

        # create a webserver to handle a single request on a free port or a specific port if passed in the parameter   
        port = 0    
        if server_port is not None:
            port = int(server_port)
        try:
            server = http.server.HTTPServer((webserver_ip, port), req_handler)
            server.socket.settimeout(10)
            self.serverthread = threading.Thread(target=server.handle_request)
            self.serverthread.start()
            url = "http://%s:%s%s" % (webserver_ip, str(server.server_port), quote_plus(filename, "/"))
        except OSError:
            url = "http://%s:%s%s" % (webserver_ip, str(server_port), quote_plus(filename, "/"))

        return url


    def local_thumb(self, bitstream, mimetype):
        """ upload thumbnail to simple http server"""

        webserver_ip =[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
        
        req_handler = local_server.ImageRequestHandler

        # create a webserver to handle a single request on a free port or a specific port if passed in the parameter   
        port = 0    
        req_handler.content_type = mimetype
        req_handler.content = bitstream

        server = http.server.HTTPServer((webserver_ip, port), req_handler)
        server.socket.settimeout(10)
        self.imagethread = threading.Thread(target=server.handle_request)
        self.imagethread.start()

        url = "http://%s:%s" % (webserver_ip, str(server.server_port))
        
        return url


    def local_sub(self, filename, mimetype):
        """serve a local subtitle file"""

        if os.path.isfile(filename):
            filename = os.path.abspath(filename)
        else:
            return None

        webserver_ip =[(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
        
        req_handler = local_server.SubtitleRequestHandler

        # create a webserver to handle a single request on a free port or a specific port if passed in the parameter   
        port = 0    

        server = http.server.HTTPServer((webserver_ip, port), req_handler)
        server.socket.settimeout(10)
        self.subtitlethread = threading.Thread(target=server.handle_request)
        self.subtitlethread.start()    

        url = "http://%s:%s%s" % (webserver_ip, str(server.server_port), quote_plus(filename, "/"))
        return url


    def get_active_chromecasts(self):
        casts = list(pyc.get_chromecasts_as_dict().keys())
        self.chromecasts = list(casts)
        return self.chromecasts



if __name__ == '__main__':
    import sys
    win = ChromecastPlayer(sys.argv[1:])
    win.run()
