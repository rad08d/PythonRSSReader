#!/usr/bin/env python

import os
import pygtk
pygtk.require('2.0')
import gtk

class Base:
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
	self.window.set_position(gtk.WIN_POS_CENTER)
	self.window.set_title("Rss Reader")
        self.window.set_default_size(800,500)
        dirName = os.path.dirname(__file__)
        path = dirName + "/images/rssReader.jpg"
	self.window.set_icon_from_file(path)
        self.startButton = gtk.Button("Start")
        self.startButton.connect("clicked", self.startButtonCallBack)
	self.box1 = gtk.VBox()
        self.box1.pack_start(self.startButton)
        self.window.add(self.box1)
	self.window.show_all()
	self.window.connect("destroy", self.destroy)

    def startButtonCallBack(self, widget):
        dirName = os.path.dirname(__file__)
        script = dirName + "/rssStart.py"
        os.system(script)
    def destroy(self, widget, data=None):
         gtk.main_quit()
    def main(self):
        gtk.main()

if __name__ == "__main__":
    base = Base()
    base.main()
