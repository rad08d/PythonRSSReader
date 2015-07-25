#!/usr/bin/python3
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2010-2012 Bryce Harrington <bryce@canonical.com>
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import absolute_import, print_function, unicode_literals

import gtk

class Application(object):
    def __init__(self):
        self.pages = {}
        self.current_page = None

        # Top level UI containers
        self.window = self.create_top_window()
        self.frame = self.create_top_frame()

        # Create UI elements
        self.accelerators = gtk.AccelGroup()

        # Assemble the UI
        self.window.add(self.frame)

        # Positions
        self.window.set_default_size(400, 300)
        self.window.set_size_request(400, 300)

    def create_top_window(self):
        win = gtk.Window(gtk.WINDOW_TOPLEVEL)
        win.connect('delete_event', self.on_delete)
        win.set_border_width(10)
        return win

    def create_top_frame(self):
        frame = gtk.Frame("")
        self.page_title = gtk.Label("")
        frame.set_label_widget(self.page_title)
        frame.set_label_align(0.0, 0.0)
        return frame

    def create_button(self, primary_text, secondary_text):
        button = gtk.Button(primary_text)
        button_label = button.get_children()[0]
        button_label.set_markup(
            "<b>%s</b>\n<small>%s</small>"
            %(primary_text, secondary_text))
        button_label.set_alignment(0.0, 0.0)
        button.set_relief(gtk.RELIEF_NONE)
        button.show()
        return button

    def create_nav_bar(self, next_page=None, prev_page=None):
        hbox_navigation = gtk.HButtonBox()

        if prev_page is not None:
            hbox_navigation.set_property("layout-style", gtk.BUTTONBOX_START)
            prev_button = gtk.Button("Back")
            prev_button.connect("clicked", self.on_page, prev_page)
            hbox_navigation.pack_start(prev_button)
        if next_page is not None:
            hbox_navigation.set_property("layout-style", gtk.BUTTONBOX_END)
            next_button = gtk.Button("Next")
            next_button.connect("clicked", self.on_page, next_page)
            hbox_navigation.pack_end(next_button)
        return hbox_navigation

    def create_page(self, text):
        page = gtk.VBox(spacing=5)
        page.set_border_width(10)
        label = gtk.Label(text)
        label.set_line_wrap(True)
        label.set_use_markup(True)
        label.set_alignment(0.0, 0.0)
        page.pack_start(label, expand=False)
        return page

    def on_delete(self, widget, event):
        gtk.main_quit()

    def on_close(self, widget):
        gtk.main_quit()
