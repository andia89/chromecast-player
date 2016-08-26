#!/usr/bin/python3

from gi import require_version
require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio, GLib
import configparser
import subprocess
import os
import re

config = configparser.ConfigParser()
configfile = os.path.expanduser('~/.config/chromecast_player')
default_vals = {'chromecast_player': {'automatic_connect': False, 'enable_web': False, 'enable_transcoding': False, 'local_port': "", 'transcoding_options':"", "preferred_transcoder":""}, 'subtitle_style':{'backgroundColor': '#ffffffff', 'foregroundColor': '#000000ff', 'edgeType': 'NONE', 'edgeColor': '#00ff00ff', 'fontScale': 1, 'fontStyle': 'NORMAL', 'fontFamily': 'Droid Sans', 'fontGenericFamily': 'SANS_SERIF', 'windowColor': '#ff0000ff', 'windowRoundedCornerRadius': 10, 'windowType': 'NONE'}}

def get_config(section):
    config.read(configfile)
    dict1 = {}
    for option in default_vals[section].keys():
        try:
            op = config.get(section, option)
            if op == 'True' or op == 'False':
                dict1[option] = (op == 'True')
            else:
                try:
                    dict1[option] = int(op)
                except:
                    dict1[option] = op
        except:
            try:    
                config.add_section(section)
            except:
                pass
            config.set(section, option, str(default_vals[section][option]))
            f = open(configfile, 'w')
            config.write(f)
            f.close()
            dict1[option] = default_vals[section][option]
    return dict1

def set_config(section, option, value):
    try:
        config.set(section, option, str(value))
    except:
        config.add_section(section)
        config.set(section, option, str(value))
    f = open(configfile, 'w')
    config.write(f)
    f.close()
    
    

class Preferences(Gtk.Window):
    
    def __init__(self):
        Gtk.Window.__init__(self)
        self.win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        config_chromecast = get_config('chromecast_player')
        vboxall = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hboxbuttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxradio = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxport = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxtrans = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self.automatic_connect = Gtk.CheckButton(label=" Automatically connect to first available chromecast on startup")
        self.automatic_connect.set_active(config_chromecast['automatic_connect'])
        self.automatic_connect.connect("toggled", self.config_changed, "automatic_connect")

        self.enable_web = Gtk.CheckButton(label=" Enable network streams")
        self.enable_web.set_active(config_chromecast['enable_web'])
        self.enable_web.connect("toggled", self.config_changed, "enable_web")
        
        self.enable_transcoding = Gtk.CheckButton(label=" Enables on the fly transcoding of unsupported filetypes")
        self.enable_transcoding.set_active(config_chromecast['enable_transcoding'])
        self.enable_transcoding.connect("toggled", self.config_changed, "enable_transcoding")
        
        radio_label = Gtk.Label()
        radio_label.set_text("Preferred transcoder: ")
        hboxradio.pack_start(radio_label, False, False, 0)
        self.ffmpeg_button = Gtk.RadioButton.new_with_label_from_widget(None, "FFMPEG")
        self.ffmpeg_button.connect("toggled", self.config_changed, "preferred_transcoder")
        hboxradio.pack_start(self.ffmpeg_button, False, False, 10)
        self.avconv_button = Gtk.RadioButton.new_with_label_from_widget(self.ffmpeg_button, "AVCONV")
        self.avconv_button.connect("toggled", self.config_changed, "preferred_transcoder")
        hboxradio.pack_start(self.avconv_button, False, False, 10)
        
        port_label = Gtk.Label()
        port_label.set_text("Port for local files: ")
        self.port_entry = Gtk.Entry()
        try:
            po = int(config_chromecast['local_port'])
            self.port_entry.set_text(str(po))
        except:
            self.port_entry.set_text("")
        self.port_entry.connect("changed", self.config_changed, "local_port")
        self.port_entry.set_max_width_chars(5)
        self.port_entry.set_width_chars(5)
        hboxport.pack_start(port_label, False, False, 0)
        hboxport.pack_start(self.port_entry, False, False, 20)
        
        transcoder_label = Gtk.Label()
        transcoder_label.set_text("Options for transcoder: ")
        self.transcoder_options = Gtk.Entry()
        self.transcoder_options.set_max_width_chars(20)
        self.transcoder_options.set_width_chars(20)
        self.transcoder_options.connect("changed", self.config_changed, "transcoding_options")
        self.transcoder_options.set_text(config_chromecast['transcoding_options'])
        hboxtrans.pack_start(transcoder_label, False, False, 0)
        hboxtrans.pack_start(self.transcoder_options, False, False, 20)
        
        if not self.enable_transcoding.get_active():
            self.ffmpeg_button.set_sensitive(False)
            self.avconv_button.set_sensitive(False)
            self.transcoder_options.set_sensitive(False)

        vboxall.pack_start(self.automatic_connect, False, False, 20)
        vboxall.pack_start(self.enable_web, False, False, 20)
        vboxall.pack_start(hboxport, False, False, 20)
        vboxall.pack_start(self.enable_transcoding, False, False, 20)
        vboxall.pack_start(hboxradio, False, False, 20)
        vboxall.pack_start(hboxtrans, False, False, 20)


        #close = Gtk.Button("_Close", use_underline=True)
        #close.get_style_context().add_class("destructive-action")
        #close.connect("clicked", self.exit)
        
        ok = Gtk.Button("_Apply", use_underline=True)
        ok.get_style_context().add_class("suggested-action")
        ok.connect("clicked", self.exit)

        self.win.connect("delete-event", Gtk.main_quit) 
        
        hboxbuttons.pack_end(ok, False, False, 30)
        vboxall.pack_end(hboxbuttons, False, False, 30)

        self.win.set_icon_name('chromecast-player')
        self.win.add(vboxall)
        self.win.set_size_request(500,50)
        self.automatic_connect.set_margin_left(30)
        self.automatic_connect.set_margin_right(50)
        self.enable_transcoding.set_margin_left(30)
        self.enable_transcoding.set_margin_right(50)
        hboxradio.set_margin_left(60)
        hboxradio.set_margin_right(20)
        hboxport.set_margin_left(30)
        hboxport.set_margin_right(50)
        hboxtrans.set_margin_left(60)
        hboxtrans.set_margin_right(20)
        self.enable_web.set_margin_left(30)
        self.enable_web.set_margin_right(50)
        self.win.set_title('Preferences')
        

    def run(self):
        self.win.show_all()
        Gtk.main()
        self.win.destroy()

    def exit(self, *args):
        #self.win.close()
        Gtk.main_quit()

    def config_changed(self, *args):
        if args[1] in ["enable_web", "enable_transcoding", "automatic_connect"]:
            state = args[0].get_active()
        elif args[1] == "preferred_transcoder":
            state = 0
        elif args[1] in ["local_port", "transcoding_options"]:
            state = args[0].get_text()
        if args[1] == "enable_web" and state:
            state = self.check_youtube_dl()
            if not state:
                message = ("Youtube-dl not installed on this machine, so stream fetching won't work!")
                win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
                dialog = Gtk.MessageDialog(win, None, Gtk.MessageType.ERROR,
                               Gtk.ButtonsType.OK, message)
                dialog.run()
                dialog.destroy()
                args[0].set_active(False)
        elif args[1] == "enable_transcoding":
            if state:
                self.transcoder_options.set_sensitive(True)
                self.ffmpeg_button.set_sensitive(True)
                self.avconv_button.set_sensitive(True)
            elif not state:
                self.transcoder_options.set_sensitive(False)
                self.ffmpeg_button.set_sensitive(False)
                self.avconv_button.set_sensitive(False)
        elif args[1] == "local_port":
            try:
                po = int(state)
                self.port_entry.set_text(str(po))
            except:
                state = ""
                self.port_entry.set_text(str(state))
        elif args[1] == "preferred_transcoder":
            if self.ffmpeg_button.get_active():
                state = 'ffmpeg'
            else:
                state = 'avconv'
        set_config('chromecast_player', args[1], str(state))
    
    def check_youtube_dl(self):
        rc = subprocess.call(['which', 'youtube-dl'])
        return bool(not rc)

EDGE_TYPE = ('NONE', 'OUTLINE', 'DROP_SHADOW', 'RAISED', 'DEPRESSED')

class SubtitleStyle(Gtk.Window):
    
    def __init__(self):
        Gtk.Window.__init__(self)
        self.win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        config_subtitles = get_config('subtitle_style')
        vboxall = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vboxconfig = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hboxconfig = []
        for i in range(len(config_subtitles)):
            hbox_config.append(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL))
        hboxexample = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxbuttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)


        self.background_color = Gtk.Entry()
        try:
            col = int(config_subtitles['backgroundColor'])
            match = re.search(r'^#(?:[0-9a-fA-F]{1,2}){4}$', col)
            if match:
                self.background_color.set_text(str(po))
            else:
                self.background_color.set_text("")
        except:
            self.background_color.set_text("")
        background_color_label = Gtk.Label()
        background_color_label.set_text("Background color: ")
        
        self.foreground_color = Gtk.Entry()
        try:
            col = int(config_subtitles['foregroundColor'])
            match = re.search(r'^#(?:[0-9a-fA-F]{1,2}){4}$', col)
            if match:
                self.foreground_color.set_text(str(po))
            else:
                self.foreground_color.set_text("")
        except:
            self.foreground_color.set_text("")
        foreground_color_label = Gtk.Label()
        foreground_color_label.set_text("Foreground color: ")

        clientstore = Gtk.ListStore(str)
        for i in EDGE_TYPE:
            clientstore.append(i)
        self.edge_type = Gtk.ComboBox.new_with_model(clientstore)
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_fixed_size(120, 20)
        self.edge_type.pack_start(renderer_text, True)
        self.edge_type.add_attribute(renderer_text, "text", 0)
        edge = config_subtitles['edgeType']
        if edge in EDGE_TYPE:
            ind = EDGE_TYPE.index(edge)
        else:
            ind = -1
        self.edge_type.set_active(ind)
        edge_type_label = Gtk.Label()
        edge_type_label.set_text("Edge type: ")

        self.edge_color = Gtk.Entry()
        try:
            col = int(config_subtitles['edgeColor'])
            match = re.search(r'^#(?:[0-9a-fA-F]{1,2}){4}$', col)
            if match:
                self.edge_color.set_text(str(po))
            else:
                self.edge_color.set_text("")
        except:
            self.edge_color.set_text("")
        edge_color_label = Gtk.Label()
        edge_color_label.set_text("Edge color: ")

        font_scale = Gtk.Scale()

        vboxall.pack_start(self.automatic_connect, False, False, 20)
        vboxall.pack_start(self.enable_web, False, False, 20)
        vboxall.pack_start(hboxport, False, False, 20)
        vboxall.pack_start(self.enable_transcoding, False, False, 20)
        vboxall.pack_start(hboxradio, False, False, 20)
        vboxall.pack_start(hboxtrans, False, False, 20)


        #close = Gtk.Button("_Close", use_underline=True)
        #close.get_style_context().add_class("destructive-action")
        #close.connect("clicked", self.exit)
        
        ok = Gtk.Button("_Apply", use_underline=True)
        ok.get_style_context().add_class("suggested-action")
        ok.connect("clicked", self.exit)

        self.win.connect("delete-event", Gtk.main_quit) 
        
        hboxbuttons.pack_end(ok, False, False, 30)
        vboxall.pack_end(hboxbuttons, False, False, 30)

        self.win.set_icon_name('chromecast-player')
        self.win.add(vboxall)
        self.win.set_size_request(500,50)
        self.automatic_connect.set_margin_left(30)
        self.automatic_connect.set_margin_right(50)
        self.enable_transcoding.set_margin_left(30)
        self.enable_transcoding.set_margin_right(50)
        hboxradio.set_margin_left(60)
        hboxradio.set_margin_right(20)
        hboxport.set_margin_left(30)
        hboxport.set_margin_right(50)
        hboxtrans.set_margin_left(60)
        hboxtrans.set_margin_right(20)
        self.enable_web.set_margin_left(30)
        self.enable_web.set_margin_right(50)
        self.win.set_title('Preferences')
        

    def run(self):
        self.win.show_all()
        Gtk.main()
        self.win.destroy()

    def exit(self, *args):
        #self.win.close()
        Gtk.main_quit()

    def config_changed(self, *args):
        if args[1] in ["enable_web", "enable_transcoding", "automatic_connect"]:
            state = args[0].get_active()
        elif args[1] == "preferred_transcoder":
            state = 0
        elif args[1] in ["local_port", "transcoding_options"]:
            state = args[0].get_text()
        if args[1] == "enable_web" and state:
            state = self.check_youtube_dl()
            if not state:
                message = ("Youtube-dl not installed on this machine, so stream fetching won't work!")
                win = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
                dialog = Gtk.MessageDialog(win, None, Gtk.MessageType.ERROR,
                               Gtk.ButtonsType.OK, message)
                dialog.run()
                dialog.destroy()
                args[0].set_active(False)
        elif args[1] == "enable_transcoding":
            if state:
                self.transcoder_options.set_sensitive(True)
                self.ffmpeg_button.set_sensitive(True)
                self.avconv_button.set_sensitive(True)
            elif not state:
                self.transcoder_options.set_sensitive(False)
                self.ffmpeg_button.set_sensitive(False)
                self.avconv_button.set_sensitive(False)
        elif args[1] == "local_port":
            try:
                po = int(state)
                self.port_entry.set_text(str(po))
            except:
                state = ""
                self.port_entry.set_text(str(state))
        elif args[1] == "preferred_transcoder":
            if self.ffmpeg_button.get_active():
                state = 'ffmpeg'
            else:
                state = 'avconv'
        set_config('chromecast_player', args[1], str(state))
    
    def check_youtube_dl(self):
        rc = subprocess.call(['which', 'youtube-dl'])
        return bool(not rc)
    


