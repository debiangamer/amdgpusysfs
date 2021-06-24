#!/usr/bin/python

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

from os import listdir
from os.path import isdir, isfile, join, realpath, basename

class Node(object):
    __slots__ = ['_path_', '__dict__']

    def __init__(self, path='/sys'):
        self._path_ = realpath(path)
        if not self._path_.startswith('/sys/') and not '/sys' == self._path_:
            raise RuntimeError('Using this on non-sysfs files is dangerous!')

        self.__dict__.update(dict.fromkeys(listdir(self._path_)))

    def __repr__(self):
        return '<sysfs.Node "%s">' % self._path_

    def __str__(self):
        return basename(self._path_)

    def __setattr__(self, name, val):
        if name.startswith('_'):
            return object.__setattr__(self, name, val)

        path = realpath(join(self._path_, name))
        if isfile(path):
            with open(path, 'w') as fp:
                fp.write(val)
        else:
            raise RuntimeError('Cannot write to non-files.')

    def __getattribute__(self, name):
        if name.startswith('_'):
            return object.__getattribute__(self, name)

        path = realpath(join(self._path_, name))
        if isfile(path):
            with open(path, 'r') as fp:
                return fp.read().strip()
        elif isdir(path):
            return Node(path)

    def __setitem__(self, name, val):
        return setattr(self, name, val)

    def __getitem__(self, name):
        return getattr(self, name)

    def __iter__(self):
        return iter(getattr(self, name) for name in listdir(self._path_))

sysgpu = Node("/sys/class/drm/card0/device/")
syscpu = Node("/sys/class/hwmon/hwmon0/")

class ClockSelectDialog(Gtk.Dialog):

    def __init__(self, parent):
        Gtk.Dialog.__init__(self, "Use", parent, 0)

        self.set_default_size(150, 100)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        clocklist = sysgpu.pp_dpm_sclk.split("\n")
        for x in clocklist:
            vbox.add(Gtk.CheckButton(x))        
        box = self.get_content_area()	
        box.add(vbox)
        self.show_all()

class MainWindow(Gtk.Window):
    
    def __init__(self):
        Gtk.Window.__init__(self, title="AmdgpuSysfs - Click Engine clock to choose clocks")
        self.box = Gtk.Box(spacing=16)
        self.add(self.box)
        self.cputempbutton=Gtk.Button()
        self.cputemplabel = Gtk.Label(label="CPU core temp:")
        self.box.pack_start(self.cputemplabel, True, True, 0)
        self.box.pack_start(self.cputempbutton, True, True, 0)
        self.gputempbutton=Gtk.Button()
        self.gputemplabel = Gtk.Label(label="GPU core temp:")
        self.box.pack_start(self.gputemplabel, True, True, 0)
        self.box.pack_start(self.gputempbutton, True, True, 0)
        self.enginebutton=Gtk.Button()
        self.enginelabel = Gtk.Label(label="Engine clock:")
        self.box.pack_start(self.enginelabel, True, True, 0)
        self.box.pack_start(self.enginebutton, True, True, 0)
        self.membutton=Gtk.Button()
        self.memlabel = Gtk.Label(label="Memory clock:")
        self.box.pack_start(self.memlabel, True, True, 0)
        self.box.pack_start(self.membutton, True, True, 0)
        self.selected = False
	
        self.enginebutton.connect("clicked", self.enginebuttonclicked)

    def enginebuttonclicked(self, button):
        dialog = ClockSelectDialog(self)
        response = dialog.run()
        y=0
        selectedstr = ""
        
        for x in dialog.get_children()[0].get_children()[0].get_children():
            value = x.get_active()
            if value:
                self.selected = True
                selectedstr = selectedstr +str(y)+" "
          
            y = y +1
        if self.selected:
             sysgpu.power_dpm_force_performance_level = "manual"
             sysgpu.pp_dpm_sclk = selectedstr
             
        dialog.destroy()
	
    def counter(self):	  
        self.cputempbutton.set_label(str(int(syscpu.temp1_input)/1000) + "C")
        self.gputempbutton.set_label(str(int(sysgpu.hwmon.hwmon2.temp1_input)/1000) + "C")
        self.enginebutton.set_label(sysgpu.pp_dpm_sclk)
        self.membutton.set_label(sysgpu.pp_dpm_mclk)
        return True

win = MainWindow()
source_id = GLib.timeout_add(2000, win.counter)

win.connect("delete-event", Gtk.main_quit)
win.show_all()
Gtk.main() 
if win.selected:
    sysgpu.power_dpm_force_performance_level = "auto"
  
GLib.source_remove(source_id)  

