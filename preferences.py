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
default_vals = {'chromecast_player': {'automatic_connect': False, 'enable_web': False, 'enable_transcoding': False, 'local_port': "", 'transcoding_options':"", "preferred_transcoder":""}, 'subtitle_style':{'backgroundColor': '#00000000', 'foregroundColor': '#000000ff', 'edgeType': 'NONE', 'edgeColor': '#00ff00ff', 'fontScale': 1.2, 'fontStyle': 'BOLD', 'fontFamily': 'Droid Sans', 'fontGenericFamily': 'SANS_SERIF', 'windowColor': '#ff0000ff', 'windowRoundedCornerRadius': 10, 'windowType': 'NONE'}}
EDGE_TYPE = ('NONE', 'OUTLINE', 'DROP_SHADOW', 'RAISED', 'DEPRESSED')
FONT_STYLE = ('NORMAL', 'BOLD', 'BOLD_ITALIC', 'ITALIC')
FONT_FAMILY = ('Droid Sans', 'Droid Sans Mono', 'Droid Serif Regular', 'Cutive Mono', 'Short Stack', 'Quintessential', 'Alegreya Sans SC')
FONT_GENERIC_FAMILY = ('SANS_SERIF', 'MONOSPACED_SANS_SERIF', 'SERIF', 'MONOSPACED_SERIF', 'CASUAL', 'CURSIVE', 'SMALL_CAPITALS')
WINDOW_TYPE = ('NONE', 'NORMAL', 'ROUNDED_CORNERS')


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
        self.notebook = Gtk.Notebook()
        self.general_preferences()
        self.styled_preferences()
        self.win.set_title('Preferences')
        self.win.add(self.notebook)
        self.win.connect("delete-event", Gtk.main_quit) 
        self.win.set_icon_name('chromecast-player')
        self.win.set_size_request(500,50)


    def general_preferences(self):
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

        hboxbuttons.pack_end(ok, False, False, 30)
        vboxall.pack_end(hboxbuttons, False, False, 30)

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
        self.notebook.append_page(vboxall, Gtk.Label('General'))


    def styled_preferences(self):
        config_subtitles = get_config('subtitle_style')
        vboxall = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hboxconfigall = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vboxconfig = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vboxlabel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        hboxexample = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxbuttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hboxlabel = []
        for i in range(11):
            hboxlabel.append(Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL))

        self.background_color = Gtk.Entry()
        try:
            col = config_subtitles['backgroundColor']
            match = re.search(r'^#(?:[0-9a-fA-F]{1,2}){4}$', col)
            if match:
                self.background_color.set_text(str(col))
            else:
                self.background_color.set_text("")
        except:
            self.background_color.set_text("")
        background_color_label = Gtk.Label()
        background_color_label.set_text("Background color: ")
        hboxlabel[0].pack_end(background_color_label, False, False, 10)
        vboxconfig.pack_start(self.background_color, True, True, 10)
        self.background_color.connect("activate", self.config_changed_subtitles, "backgroundColor")
        self.background_color.connect("focus-out-event", self.config_changed_subtitles, "backgroundColor")


        self.foreground_color = Gtk.Entry()
        try:
            col = config_subtitles['foregroundColor']
            match = re.search(r'^#(?:[0-9a-fA-F]{1,2}){4}$', col)
            if match:
                self.foreground_color.set_text(str(col))
            else:
                self.foreground_color.set_text("")
        except:
            self.foreground_color.set_text("")
        foreground_color_label = Gtk.Label()
        foreground_color_label.set_text("Foreground color: ")
        hboxlabel[1].pack_end(foreground_color_label, False, False, 10)
        vboxconfig.pack_start(self.foreground_color, True, True, 10)
        self.foreground_color.connect("activate", self.config_changed_subtitles, "foregroundColor")
        self.foreground_color.connect("focus-out-event", self.config_changed_subtitles, "foregroundColor")

        clientstore = Gtk.ListStore(str)
        for i in EDGE_TYPE:
            clientstore.append([i])
        self.edge_type = Gtk.ComboBox.new_with_model(clientstore)
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_fixed_size(120, 20)
        self.edge_type.pack_start(renderer_text, True)
        self.edge_type.add_attribute(renderer_text, "text", 0)
        edge = config_subtitles['edgeType']
        if edge in EDGE_TYPE:
            ind = EDGE_TYPE.index(edge)
        else:
            ind = EDGE_TYPE.index(default_vals['subtitle_style']['edgeType'])
        self.edge_type.set_active(ind)
        edge_type_label = Gtk.Label()
        edge_type_label.set_text("Edge type: ")
        hboxlabel[2].pack_end(edge_type_label, False, False, 10)
        vboxconfig.pack_start(self.edge_type, True, True, 10)
        self.edge_type.connect("changed", self.config_changed_subtitles, "edgeType")


        self.edge_color = Gtk.Entry()
        try:
            col = config_subtitles['edgeColor']
            match = re.search(r'^#(?:[0-9a-fA-F]{1,2}){4}$', col)
            if match:
                self.edge_color.set_text(str(col))
            else:
                self.edge_color.set_text("")
        except:
            self.edge_color.set_text("")
        edge_color_label = Gtk.Label()
        edge_color_label.set_text("Edge color: ")
        hboxlabel[3].pack_end(edge_color_label, False, False, 10)
        vboxconfig.pack_start(self.edge_color, True, True, 10)
        self.edge_color.connect("activate", self.config_changed_subtitles, "edgeColor")
        self.edge_color.connect("focus-out-event", self.config_changed_subtitles, "edgeColor")

        self.font_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 5, 0.1)
        try:
            scale = round(float(config_subtitles['fontScale']),1)
            self.font_scale.set_value(scale)
        except:
            self.font_scale.set_value(1)
        font_scale_label = Gtk.Label()
        font_scale_label.set_text("Font scale: ")
        hboxlabel[4].pack_end(font_scale_label, False, False, 10)
        vboxconfig.pack_start(self.font_scale, True, True, 10)
        self.font_scale.connect("value-changed", self.config_changed_subtitles, "fontScale")


        clientstore = Gtk.ListStore(str)
        for i in FONT_STYLE:
            clientstore.append([i])
        self.font_style = Gtk.ComboBox.new_with_model(clientstore)
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_fixed_size(120, 20)
        self.font_style.pack_start(renderer_text, True)
        self.font_style.add_attribute(renderer_text, "text", 0)
        style = config_subtitles['fontStyle']
        if style in FONT_STYLE:
            ind = FONT_STYLE.index(style)
        else:
            ind = FONT_STYLE.index(default_vals['subtitle_style']['fontStyle'])
        self.font_style.set_active(ind)
        font_style_label = Gtk.Label()
        font_style_label.set_text("Font style: ")
        hboxlabel[5].pack_end(font_style_label, False, False, 10)
        vboxconfig.pack_start(self.font_style, True, True, 10)
        self.font_style.connect("changed", self.config_changed_subtitles, "fontStyle")


        clientstore = Gtk.ListStore(str)
        for i in FONT_FAMILY:
            clientstore.append([i])
        self.font_family = Gtk.ComboBox.new_with_model(clientstore)
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_fixed_size(120, 20)
        self.font_family.pack_start(renderer_text, True)
        self.font_family.add_attribute(renderer_text, "text", 0)
        fam = config_subtitles['fontFamily']
        if fam in FONT_FAMILY:
            ind = FONT_FAMILY.index(fam)
        else:
            ind = FONT_FAMILY.index(default_vals['subtitle_style']['fontFamily'])
        self.font_family.set_active(ind)
        font_family_label = Gtk.Label()
        font_family_label.set_text("Font family: ")
        hboxlabel[6].pack_end(font_family_label, False, False, 10)
        vboxconfig.pack_start(self.font_family, True, True, 10)
        self.font_family.connect("changed", self.config_changed_subtitles, "fontFamily")


        clientstore = Gtk.ListStore(str)
        for i in FONT_GENERIC_FAMILY:
            clientstore.append([i])
        self.font_generic_family = Gtk.ComboBox.new_with_model(clientstore)
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_fixed_size(120, 20)
        self.font_generic_family.pack_start(renderer_text, True)
        self.font_generic_family.add_attribute(renderer_text, "text", 0)
        fam = config_subtitles['fontGenericFamily']
        if fam in FONT_GENERIC_FAMILY:
            ind = FONT_GENERIC_FAMILY.index(fam)
        else:
            ind = FONT_GENERIC_FAMILY.index(default_vals['subtitle_style']['fontGenericFamily'])
        self.font_generic_family.set_active(ind)
        font_generic_family_label = Gtk.Label()
        font_generic_family_label.set_text("Font generic family: ")
        hboxlabel[7].pack_end(font_generic_family_label, False, False, 10)
        vboxconfig.pack_start(self.font_generic_family, True, True, 10)
        self.font_generic_family.connect("changed", self.config_changed_subtitles, "fontGenericFamily")


        self.window_color = Gtk.Entry()
        try:
            col = config_subtitles['windowColor']
            match = re.search(r'^#(?:[0-9a-fA-F]{1,2}){4}$', col)
            if match:
                self.window_color.set_text(str(col))
            else:
                self.window_color.set_text("")
        except:
            self.window_color.set_text("")
        window_color_label = Gtk.Label()
        window_color_label.set_text("Window color: ")
        hboxlabel[8].pack_end(window_color_label, False, False, 10)
        vboxconfig.pack_start(self.window_color, True, True, 10)
        self.window_color.connect("activate", self.config_changed_subtitles, "windowColor")
        self.window_color.connect("focus-out-event", self.config_changed_subtitles, "windowColor")

        radius_label = Gtk.Label()
        radius_label.set_text("Window corner radius (px): ")
        self.radius_entry = Gtk.Entry()
        try:
            po = int(config_subtitles['windowRoundedCornerRadius'])
            self.radius_entry.set_text(str(po))
        except:
            self.radius_entry.set_text("1")
        hboxlabel[9].pack_end(radius_label, False, False, 10)
        vboxconfig.pack_start(self.radius_entry, True, True, 10)
        self.radius_entry.connect("activate", self.config_changed_subtitles, "windowRoundedCornerRadius")
        self.radius_entry.connect("focus-out-event", self.config_changed_subtitles, "windowRoundedCornerRadius")

        clientstore = Gtk.ListStore(str)
        for i in WINDOW_TYPE:
            clientstore.append([i])
        self.window_type = Gtk.ComboBox.new_with_model(clientstore)
        renderer_text = Gtk.CellRendererText()
        renderer_text.set_fixed_size(120, 20)
        self.window_type.pack_start(renderer_text, True)
        self.window_type.add_attribute(renderer_text, "text", 0)
        ty = config_subtitles['windowType']
        if ty in WINDOW_TYPE:
            ind = WINDOW_TYPE.index(ty)
        else:
            ind = WINDOW_TYPE.index(default_vals['subtitle_style']['windowType'])
        self.window_type.set_active(ind)
        window_type_label = Gtk.Label()
        window_type_label.set_text("Window Type: ")
        hboxlabel[10].pack_end(window_type_label, False, False, 10)
        vboxconfig.pack_start(self.window_type, True, True, 10)
        self.window_type.connect("changed", self.config_changed_subtitles, "windowType")

        for box in hboxlabel:
            vboxlabel.pack_start(box, True, True, 10)

        hboxconfigall.pack_start(vboxlabel, True, True, 10)
        hboxconfigall.pack_start(vboxconfig, True, True, 10)

        
        ok = Gtk.Button("_Apply", use_underline=True)
        ok.get_style_context().add_class("suggested-action")
        ok.connect("clicked", self.exit)
        

        vboxconfig.set_margin_right(50)
        vboxall.pack_start(hboxconfigall, False, False, 20)
        hboxbuttons.pack_end(ok, False, False, 30)
        vboxall.pack_end(hboxbuttons, False, False, 40)

        self.notebook.append_page(vboxall, Gtk.Label('Subtitle style'))


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
            state = check_youtube_dl()
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


    def config_changed_subtitles(self, *args):
        if args[-1] in ["edgeType", "fontGenericFamily", "fontStyle", "fontFamily", "windowType"]:
            it = args[0].get_active_iter()
            model = args[0].get_model()
            state = model.get_value(it, 0)
        elif args[-1] in ["backgroundColor", "foregroundColor", "edgeColor", "windowColor"]:
            text = args[0].get_text()
            match = re.search(r'^#(?:[0-9a-fA-F]{1,2}){4}$', text)
            if match:
                state = text
            else:
                state = default_vals['subtitle_style'][args[-1]]
                args[0].set_text(state)
        elif args[-1] == "fontScale":
            state = round(float(args[0].get_value()), 1)
        elif args[-1] == "windowRoundedCornerRadius":
            try:
                state = int(args[0].get_text())
            except:
                state = 1
                args[0].set_text(str(state))
        set_config('subtitle_style', args[-1], str(state))


def check_youtube_dl():
    rc = subprocess.call(['which', 'youtube-dl'])
    return bool(not rc)

