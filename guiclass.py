#!/usr/bin/env python
import gobject
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
        self.window.set_default_size(1500,1000)
        self.swindow = gtk.ScrolledWindow()
        self.vbox = gtk.VBox()
        self.dirName = os.path.dirname(__file__)
        path = self.dirName + "/images/rssReader.jpg"
        self.tree = self.display_data()
        self.selection = self.tree.get_selection()
        self.selection.connect("changed", self.on_selection)
	self.window.set_icon_from_file(path)
        self.swindow.add(self.tree)
        self.vbox.add(self.swindow)
        self.window.add(self.vbox)
	self.window.show_all()
	self.window.connect("destroy", self.destroy)
    
    def on_selection(self, tree_selection):
        (model, path) = tree_selection.get_selected()
        print path
        article = model.get_value(path, 2)
        article.get_full_txt()
        article_window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        article_window.set_position(gtk.WIN_POS_MOUSE)
        article_window.set_title(article.title)
        article_window.set_default_size(1000,500)
        article_swindow = gtk.ScrolledWindow()
        article_buf = gtk.TextBuffer()
        article_buf.set_text(article.full_txt)
        article_txt_view = gtk.TextView(article_buf)
        article_txt_view.set_editable(False)
        article_txt_view.set_cursor_visible(False)
        article_txt_view.set_wrap_mode(gtk.WRAP_WORD)
        article_txt_view.set_indent(60)
        article_txt_view.set_left_margin(30)
        article_txt_view.set_right_margin(30)
        article_txt_view.set_pixels_above_lines(20)
        article_txt_view.set_pixels_below_lines(20)
        article_swindow.add(article_txt_view)
        article_window.add(article_swindow)
        article_window.show_all()
            

    def display_data(self):
        store = gtk.ListStore(str, str, gobject.TYPE_PYOBJECT)
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
                        store.append([article.title, article.pubDate, article]) 
                tree = gtk.TreeView(store)
                renderer = gtk.CellRendererText()
                columnT = gtk.TreeViewColumn("Title", renderer, text=0)
                tree.append_column(columnT)
                columnPubDate = gtk.TreeViewColumn("PubDate", renderer, text=1)
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
