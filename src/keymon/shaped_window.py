#!/usr/bin/python3
#
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Create a shaped window to show mouse events.

Thanks to mathias.gumz for the original code.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import \
    GObject, \
    Gdk, \
    Gtk

from . import lazy_pixbuf_creator

class ShapedWindow(Gtk.Window):
    """Create a window shaped as fname."""

    def __init__(self, fname, scale=1.0, timeout=0.2):
        Gtk.Window.__init__(self)
        self.connect('size-allocate', self._on_size_allocate)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_accept_focus(False)
        self.scale = scale
        self.shown = False
        self.timeout = timeout
        self.timeout_timer = None
        self.name_fnames = {
          'mouse' : [fname],
        }
        self.pixbufs = lazy_pixbuf_creator.LazyPixbufCreator(self.name_fnames,
                                                             self.scale)
        self.pixbuf = self.pixbufs.get('mouse')
        self.resize(self.pixbuf.get_width(), self.pixbuf.get_height())

        # a pixmap widget to contain the pixmap
        self.image = Gtk.Image()
        self.image.set_from_pixbuf(self.pixbuf)
        self.image.show()
        self.add(self.image)
    #end __init__

    def _on_size_allocate(self, win, unused_allocation):
        """Called when first allocated."""
        # Set the window shape
        #win.get_property("window").shape_combine_region(self.mask, 0, 0)
          # FIXME: GTK 3 wants a Cairo region, but Cairo offers no function
          # to generate a region from a bitmap.
        win.set_property('skip-taskbar-hint', True)
        if not win.is_composited():
            print('Unable to fade the window')
        else:
            win.set_opacity(0.5)
        #end if
    #end _on_size_allocate

    def center_on_cursor(self, x=None, y=None):
        if x is None or y is None:
            root = Gdk.get_default_root_window()
            _, x, y, _ = root.get_pointer()
        #end if
        w, h = self.get_size()
        new_x, new_y = x - w/2, y - h/2
        pos = self.get_position()
        if pos[0] != new_x or pos[1] != new_y:
            self.move(new_x, new_y)
            self.show()
        #end if
    #end center_on_cursor

    def show(self):
        """Show this mouse indicator and ignore awaiting fade away request."""
        if self.timeout_timer and self.shown:
          # There is a fade away request, ignore it
          GObject.source_remove(self.timeout_timer)
          self.timeout_timer = None
          # This method only is called when mouse is pressed, so there will be a
          # release and fade_away call, no need to set up another timer.
        #end if
        super(ShapedWindow, self).show()
    #end show

    def maybe_show(self):
        if self.shown or not self.timeout_timer:
            return
        self.shown = True
        self.show()
    #end maybe_show

    def delayed_hide(self) :
        self.hide()
        self.timeout_timer = None
          # so I don’t try to remove expired timer
        return False
    #end delayed_hide

    def fade_away(self):
        """Make the window fade in a little bit."""
        # TODO this isn't doing any fading out
        self.shown = False
        self.timeout_timer = GObject.timeout_add(int(self.timeout * 1000), self.delayed_hide)
    #end fade_away

#end ShapedWindow
