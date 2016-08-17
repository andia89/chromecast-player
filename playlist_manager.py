from gi import require_version
require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, GLib
import helpers
from stream_select import FileChooserWindow, NetworkStream



class PlaylistManager(Gtk.Window):
    def __init__(self, playlist, enable_web, transcoder, probe, preferred_transcoder, counter):
        self.win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)

        theme = Gtk.IconTheme.get_default()
        self.playimage = theme.load_icon("media-playback-start", 16,0)
        self.store = Gtk.ListStore(GdkPixbuf.Pixbuf, str, str, int, int, str, str, str, str)
        self.selection_index = None 
        self.create_model(playlist)
        if counter:
            self.store[counter][0] = self.playimage
        self.playlist_counter = None
        self.play_now = False
        self.playlist_changed = False
        self.playlist_counter_changed = False
        self.double_clicked = False
        self.transcoder = transcoder
        self.number_clicked = 0
        self.probe = probe
        self.preferred_transcoder = preferred_transcoder
        self.enable_web = enable_web
        self.show_image = True


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
        vboxall = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vboxmanager = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hboxbuttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        filebutton = Gtk.Button('_Open', use_underline=True)
        filebutton.connect('clicked', self._on_file_clicked)

        self.netbutton = Gtk.Button('_Open network stream', use_underline=True)
        self.netbutton.connect('clicked', self._on_net_stream_clicked)

        deletebutton = Gtk.Button()
        deleteButtonImage = Gtk.Image()
        deleteButtonImage.set_from_stock(Gtk.STOCK_REMOVE, Gtk.IconSize.BUTTON)
        deletebutton.add(deleteButtonImage)

        topbutton = Gtk.Button()
        topButtonImage = Gtk.Image()
        topButtonImage.set_from_stock(Gtk.STOCK_GOTO_TOP, Gtk.IconSize.BUTTON)
        topbutton.add(topButtonImage)

        upbutton = Gtk.Button()
        upButtonImage = Gtk.Image()
        upButtonImage.set_from_stock(Gtk.STOCK_GO_UP, Gtk.IconSize.BUTTON)
        upbutton.add(upButtonImage)

        bottombutton = Gtk.Button()
        bottomButtonImage = Gtk.Image()
        bottomButtonImage.set_from_stock(Gtk.STOCK_GOTO_BOTTOM, Gtk.IconSize.BUTTON)
        bottombutton.add(bottomButtonImage)

        downbutton = Gtk.Button()
        downButtonImage = Gtk.Image()
        downButtonImage.set_from_stock(Gtk.STOCK_GO_DOWN, Gtk.IconSize.BUTTON)
        downbutton.add(downButtonImage)

        okbutton = Gtk.Button('_Close', use_underline=True)
        okbutton.connect("clicked", self.exit)

        mainmenu = Gtk.Menu()
        filem = Gtk.MenuItem("Open")
        self.streamm = Gtk.MenuItem("Open network stream")
        if not self.enable_web:
            self.streamm.set_sensitive(False)
        exit = Gtk.MenuItem("Close")
        root_menu = Gtk.MenuItem('File')
        root_menu.set_submenu(mainmenu)
        menu_bar = Gtk.MenuBar()
        mainmenu.append(filem)
        mainmenu.append(self.streamm)
        mainmenu.append(exit)
        menu_bar.append(root_menu)

        sw = Gtk.ScrolledWindow()
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.treeView = Gtk.TreeView(self.store)
        self.create_columns(self.treeView)
        sw.add(self.treeView)
        
        okbutton.set_margin_right(10)
        filebutton.set_margin_left(10)
        deletebutton.set_margin_left(200)
        hboxbuttons.pack_start(filebutton, False, False, 0)
        hboxbuttons.pack_start(self.netbutton, False, False, 10)
        hboxbuttons.pack_start(deletebutton, False, False, 0)
        hboxbuttons.pack_start(bottombutton, False, False, 10)
        hboxbuttons.pack_start(downbutton, False, False, 0)
        hboxbuttons.pack_start(upbutton, False, False, 10)
        hboxbuttons.pack_start(topbutton, False, False, 0)
        hboxbuttons.pack_end(okbutton, False, False, 0)
        vboxmanager.pack_start(sw, True, True, 0)
        vboxall.pack_start(vboxmanager, True, True, 0)
        vboxall.pack_end(hboxbuttons, False, False, 10)
        vboxall.pack_start(menu_bar, False, False, 0)

        deletebutton.connect("clicked", self._on_delete_clicked)
        upbutton.connect("clicked", self._on_up_clicked)
        downbutton.connect("clicked", self._on_down_clicked)
        topbutton.connect("clicked", self._on_top_clicked)
        bottombutton.connect("clicked", self._on_bottom_clicked)
        filem.connect('activate', self._on_file_clicked)
        self.streamm.connect('activate', self._on_net_stream_clicked)
        exit.connect("activate", self.exit)

        self.win.set_size_request(1200, 700)
        self.win.add(vboxall)
        self.win.show_all()


    def _on_delete_clicked(self, *args):
        if len(self.store) == 1:
            self.play_uri = []
            self.delete_at_index(0)
            self.playlist_changed = True
            return
        index = self.get_selected_index()
        if self.playlist_counter is not None:
            plc = self.playlist_counter + self.number_clicked
            if plc == index and self.show_image:
                self.number_clicked += -1
                self.playlist_counter_changed = True
            elif index < plc:
                self.number_clicked += -1
                self.playlist_counter_changed = True
        self.delete_at_index(index)
        if plc == index and self.show_image:
            self.show_image = False
            self.store[index][0] = None
        self.selection_index = index - 1
        popped = self.play_uri.pop(index)
        self.playlist_changed = True


    def _on_up_clicked(self, *args):
        index = self.get_selected_index()
        if self.playlist_counter is not None:
            plc = self.playlist_counter + self.number_clicked
        else:
            plc = None
        if not index == 0:
            if self.playlist_counter is not None:
                if plc == index:
                    self.number_clicked += -1
                    self.playlist_counter_changed = True
                elif plc == index - 1:
                    self.number_clicked += 1
                    self.playlist_counter_changed = True
            self.move_item_up()
            if plc == index:
                self.store[index][0] = None
                self.store[index-1][0] = self.playimage
            elif plc == index - 1:
                self.store[index-1][0] = None
                self.store[index][0] = self.playimage
            self.selection_index = index - 1
            popped = self.play_uri.pop(index)
            self.play_uri.insert(index-1, popped)
            self.playlist_changed = True
            

    def _on_down_clicked(self, *args):
        index = self.get_selected_index()
        if self.playlist_counter is not None:
            plc = self.playlist_counter + self.number_clicked
        else:
            plc = None
        if not index == len(self.store)-1:
            if self.playlist_counter is not None:
                if plc == index:
                    self.number_clicked += 1
                    self.playlist_counter_changed = True
                elif plc == index + 1:
                    self.number_clicked += -1
                    self.playlist_counter_changed = True
            self.move_item_down()
            if plc == index:
                self.store[index][0] = None
                self.store[index+1][0] = self.playimage
            elif plc == index + 1:
                self.store[index+1][0] = None
                self.store[index][0] = self.playimage
            self.selection_index = index + 1
            popped = self.play_uri.pop(index)
            self.play_uri.insert(index+1, popped)
            self.playlist_changed = True


    def _on_top_clicked(self, *args):
        index = self.get_selected_index()
        if self.playlist_counter is not None:
            plc = self.playlist_counter + self.number_clicked
        else:
            plc = None
        if not index == 0:
            if self.playlist_counter is not None:
                if plc == index:
                    self.number_clicked += -plc
                    self.playlist_counter_changed = True
                elif index > plc:
                    self.number_clicked += 1
                    self.playlist_counter_changed = True
            self.move_item_top()
            if plc == index:
                self.store[plc][0] = None
                self.store[0][0] = self.playimage
            elif plc and index > plc:
                self.store[plc][0] = None
                self.store[plc+1][0] = self.playimage
            self.selection_index = 0
            popped = self.play_uri.pop(index)
            self.play_uri.insert(0, popped)
            self.playlist_changed = True


    def _on_bottom_clicked(self, *args):
        index = self.get_selected_index()
        if self.playlist_counter is not None:
            plc = self.playlist_counter + self.number_clicked
        else:
            plc = None
        if not index == len(self.store)-1:
            if self.playlist_counter is not None:
                if plc == index:
                    self.number_clicked += len(self.store) - plc - 1
                    self.playlist_counter_changed = True 
                elif index < plc:
                    self.number_clicked += -1
                    self.playlist_counter_changed = True
            self.move_item_bottom()
            if plc == index:
                self.store[plc][0] = None
                self.store[-1][0] = self.playimage
            elif plc and index < plc:
                self.store[plc][0] = None
                self.store[plc-1][0] = self.playimage
            self.selection_index = len(self.store)-1
            popped = self.play_uri.pop(index)
            self.play_uri.append(popped)
            self.playlist_changed = True
        
    
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


    def create_model(self, playlist):
        self.store.clear()
        self.play_uri = playlist[:]
        if playlist:
            for k in playlist:
                self.store.append([None] + self.add_to_playlist(k))
            if self.selection_index:
                self.treeView.set_cursor(self.selection_index)
                self.selection_index = None


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


    def get_selected_index(self):
        sel = self.treeView.get_selection()
        model, i = sel.get_selected()
        res = model[i].path.get_indices()
        return res[0]


    def delete_at_index(self, index):
        for row in self.store:
            if row.path.get_indices()[0] == index:
                self.store.remove(row.iter)
                break


    def move_item_down(self):
        selection = self.treeView.get_selection()
        selections, model = selection.get_selected_rows()
        for row in selections:
            if selection.iter_is_selected(row.iter) and row.next:
                print(row.next.iter)
                self.store.swap(row.iter, row.next.iter)


    def move_item_up(self):
        selection = self.treeView.get_selection()
        selections, model = selection.get_selected_rows()
        for row in selections:
            if selection.iter_is_selected(row.iter) and row.previous:
                self.store.swap(row.iter, row.previous.iter)


    def move_item_top(self):
        selection = self.treeView.get_selection()
        selections, model = selection.get_selected_rows()
        for row in selections:
            if selection.iter_is_selected(row.iter):
                self.store.move_after(row.iter)


    def move_item_bottom(self):
        selection = self.treeView.get_selection()
        selections, model = selection.get_selected_rows()
        for row in selections:
            if selection.iter_is_selected(row.iter):
                self.store.move_before(row.iter)


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













