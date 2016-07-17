#!/usr/bin/python3

from gi import require_version
require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio, GLib
import configparser
import subprocess

config = configparser.ConfigParser()
configfile = '/home/andreas/.config/chromecast_player'
default_vals = {'chromecast_player': {'automatic_connect': False, 'enable_web': False}}

def get_config(section):
    config.read(configfile)
    dict1 = {}
    for option in default_vals[section].keys():
        try:
            dict1[option] = (config.get(section, option) == 'True')
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

        self.automatic_connect = Gtk.CheckButton(label=" Automatically connect to first available chromecast on startup")
        self.automatic_connect.set_active(config_chromecast['automatic_connect'])
        self.automatic_connect.connect("toggled", self.config_changed, "automatic_connect")

        self.enable_web = Gtk.CheckButton(label=" Enable network streams")
        self.enable_web.set_active(config_chromecast['enable_web'])
        self.enable_web.connect("toggled", self.config_changed, "enable_web")
        
        vboxall.pack_start(self.automatic_connect, False, False, 20)
        vboxall.pack_start(self.enable_web, False, False, 20)


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
        state = args[0].get_active()
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
        set_config('chromecast_player', args[1], str(state))
    
    def check_youtube_dl(self):
        rc = subprocess.call(['which', 'youtube-dl'])
        return bool(not rc)
    


