#!/usr/bin/env python

import os
import pygtk
pygtk.require('2.0')
import gtk
from RssClass import Rss
import sys

class Base:
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
	self.window.set_position(gtk.WIN_POS_CENTER)
	self.window.set_title("Rss Reader")
        self.window.set_default_size(800,500)
        self.dirName = os.path.dirname(__file__)
        path = self.dirName + "/images/rssReader.jpg"
        self.tree = self.display_data()
	self.window.set_icon_from_file(path)
        self.window.add(self.tree)
	self.window.show_all()
	self.window.connect("destroy", self.destroy)

    def display_data(self):
        store = gtk.ListStore(str, str, str)
        try:
            path = self.dirName + "/rssWebSites.txt"
            file = open(path)
            sites = file.readlines()
            siteStories = []
            for site in sites:
                rss = Rss(site)
                rss.get_rss_into_articles()
	        siteStories.append(rss)
            try:
                for collArticles in siteStories:
                    for article in collArticles.articles:
                        store.append([article.title, article.descr, article.pubDate]) 
                tree = gtk.TreeView(store)
                renderer = gtk.CellRendererText()
                columnT = gtk.TreeViewColumn("Title", renderer, text=0)
                tree.append_column(columnT)
                columnDescr = gtk.TreeViewColumn("Description", renderer, text=4)
                tree.append_column(columnDescr)
                columnPubDate = gtk.TreeViewColumn("PubDate", renderer, text=2)
                tree.append_column(columnPubDate)
                return tree 
            except:
                print "display_data() error in guiclass.py. Error report: ", sys.exc_info()[1]
        except IOError: 
            print "Can't find website list file. Error: " , sys.exc_info()[1]

    def destroy(self, widget, data=None):
         gtk.main_quit()
    def main(self):
        gtk.main()

if __name__ == "__main__":
    base = Base()
    base.main()
