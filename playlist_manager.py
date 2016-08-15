from gi.repository import Gtk, GdkPixbuf, GLib
import helpers
from stream_select import FileChooserWindow, NetworkStream



class PlaylistManager(Gtk.Window):
    def __init__(self, playlist, enable_web, transcoder, probe, preferred_transcoder):
        parent = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        self.win = Gtk.Dialog("My dialog",
                   parent,
                   Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                   ()
             )
        okbutton = self.win.add_button('Close', Gtk.ResponseType.OK)
        okbutton.connect("clicked", self.exit)

        filebutton = self.win.add_button('Open', Gtk.ResponseType.OK)
        filebutton.connect('clicked', self._on_file_clicked)

        netbutton = self.win.add_button('Open network stream', Gtk.ResponseType.OK)
        netbutton.connect('clicked', self._on_net_stream_clicked)

        theme = Gtk.IconTheme.get_default()
        self.playimage = theme.load_icon("media-playback-start", 16,0)
        self.store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str, int, int, str, str, str, str)
        self.create_model(playlist)
        self.playlist_counter = None
        self.play_now = True
        self.playlist_changed = False
        self.transcoder = transcoder
        self.probe = probe
        self.preferred_transcoder = preferred_transcoder
        self.enable_web = enable_web

    def exit(self, *args):
        self.win.close()

    def check_uris(self, play_uri):
        uri_win = []
        item = self.store.get_iter_first()
        while (item != None):
            uri_win.append(self.store.get_value(item, 1))
            item = self.store.iter_next(item)
        player_uri = [pl[0] for pl in play_uri]
        if uri_win != player_uri:
            self.create_model(play_uri)

    def main(self):
        self.win.set_title("Manage playlist")
        mainmenu = Gtk.Menu()
        filem = Gtk.MenuItem("Open")
        mainmenu.append(filem)
        self.streamm = Gtk.MenuItem("Open network stream")
        mainmenu.append(self.streamm)
        if not self.enable_web:
            self.streamm.set_sensitive(False)

        exit = Gtk.MenuItem("Close")

        mainmenu.append(exit)

        root_menu = Gtk.MenuItem('File')
        root_menu.set_submenu(mainmenu)

        menu_bar = Gtk.MenuBar()
        menu_bar.append(root_menu)

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.win.set_size_request(1200, 700)
        content_area = self.win.get_content_area()
        
        content_area.pack_start(menu_bar, False, False, 2)
        content_area.pack_start(sw, True, True, 10)
        self.treeView = Gtk.TreeView(self.store)
        exit.connect("activate", self.exit)
        self.create_columns(self.treeView)
        sw.add(self.treeView)

        filem.connect('activate', self._on_file_clicked)
        self.streamm.connect('activate', self._on_net_stream_clicked)

        self.win.show_all()
        GLib.timeout_add(500, self._playlist_counter_watch)

    
    def _on_file_clicked(self, *args):
        win = FileChooserWindow()
        ret = win.main()
        playlist = self.play_uri.copy()
        if ret:
            if ret[1] == 1:
                self.play_now = True
                self.play_uri = []
                for i,u in enumerate(ret[0]):
                    self.play_uri.append(helpers.decode_local_uri(u, self.transcoder, self.probe, self.preferred_transcoder))
            else:
                for i, u in enumerate(ret[0]):
                    self.play_uri.append(helpers.decode_local_uri(u, self.transcoder, self.probe, self.preferred_transcoder))
            self.playlist_changed = True


    def _on_net_stream_clicked(self, *args):
        win = NetworkStream()
        ret = win.main()
        playlist = self.play_uri.copy()
        if ret:
            if ret[1] == 1:
                self.play_now = True
                self.play_uri = []
                n = helpers.decode_network_uri(ret[0])
                if n:
                    self.play_uri.append(n)
            else:
                n = helpers.decode_network_uri(ret[0])
                if n:
                    self.play_uri.append(n)
            self.playlist_changed = True


    def _playlist_counter_watch(self):
        if not self.win.is_visible():
            return False
        for row in self.store:
            row[0] = None
        if self.playlist_counter is not None:
            self.store[self.playlist_counter][0] = self.playimage
        return True
        

    def create_model(self, playlist):
        self.store.clear()
        self.play_uri = playlist[:]
        if playlist:
            for k in playlist:
                self.store.append([None] + self.add_to_playlist(k))


    def create_columns(self, treeView):
        rendererPixbuf = Gtk.CellRendererPixbuf()
        column = Gtk.TreeViewColumn(None, rendererPixbuf, pixbuf=0)
        column.set_sort_column_id(0)
        column.set_resizable(False) 
        treeView.append_column(column)

        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("URI", rendererText, text=1)
        column.set_spacing(50)
        column.set_fixed_width(180)
        column.set_sort_column_id(1)  
        column.set_resizable(True)
        treeView.append_column(column)
        
        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Title", rendererText, text=2)
        column.set_sort_column_id(2)
        column.set_spacing(50)
        column.set_fixed_width(180)
        column.set_resizable(True)
        treeView.append_column(column)

        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Nr", rendererText, text=3)
        column.set_sort_column_id(3)
        column.set_spacing(50)
        column.set_fixed_width(40)
        column.set_resizable(True)
        treeView.append_column(column)

        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("CD", rendererText, text=4)
        column.set_sort_column_id(4)
        column.set_spacing(50)
        column.set_fixed_width(40)
        column.set_resizable(True)
        treeView.append_column(column)

        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Album", rendererText, text=5)
        column.set_sort_column_id(5)
        column.set_spacing(50)
        column.set_fixed_width(180)
        column.set_resizable(True)        
        treeView.append_column(column)

        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Artist", rendererText, text=6)
        column.set_sort_column_id(6)
        column.set_spacing(50)
        column.set_fixed_width(180)
        column.set_resizable(True)
        treeView.append_column(column)

        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("AlbumArtist", rendererText, text=7)
        column.set_sort_column_id(7)
        column.set_spacing(50)
        column.set_fixed_width(180)
        column.set_resizable(True)
        treeView.append_column(column)
        
        rendererText = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Composer", rendererText, text=8)
        column.set_sort_column_id(8)
        column.set_spacing(50)
        column.set_fixed_width(180)
        column.set_resizable(True)
        treeView.append_column(column)

    def add_to_playlist(self, data):
        uri = data[0]
        metadata = data[4]
        title = None
        album = None
        artist = None
        albumartist = None
        composer = None
        track = None
        cdnumber = None         
        if metadata:
            if 'title' in metadata.keys():
                title = metadata['title']
            if 'artist' in metadata.keys():
                artist = metadata['artist']
            if 'albumArtist' in metadata.keys():
                albumartist = metadata['albumArtist']
            if 'composer' in metadata.keys():
                composer = metadata['composer']
            if 'albumName' in metadata.keys():
                album = metadata['albumName']
            if 'trackNumber' in metadata.keys():
                track = metadata['trackNumber']
            if 'cdNumber' in metadata.keys():
                cdnumber = metadata['cdNumber']
        return [uri, title, track, cdnumber, album, artist, albumartist, composer]













