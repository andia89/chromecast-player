from gi.repository import Gtk

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



