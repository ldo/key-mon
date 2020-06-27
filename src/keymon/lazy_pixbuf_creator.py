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

"""Create pixbuf on demand.

This creates a GTK pixbuf in one of 2 manners:
1) Simple filename (probably supports most image formats)
2) A function which returns bytes to a file which can be read by
   pixbuf_new_from_file().

The name_fnames contains a list for key.  Each element of the list will be
composited with the previous element (overlayed on top of).

Alpha transparencies from the new, overlayed, image are respected.
"""

__author__ = 'scott@forusers.com (Scott Kirkwood))'

import logging
import os
import sys
import cairo
import gi
gi.require_version("Gdk", "3.0")
gi.require_version("Rsvg", "2.0")
from gi.repository import \
    Gdk, \
    GdkPixbuf, \
    Rsvg

class LazyPixbufCreator:
    """Class to create SVG images on the fly."""

    def __init__(self, name_fnames, resize):
        """Initialize with empty.

        Args:
          name_fnames: List of names to filename list.
        """
        self.pixbufs = {}
        self.resize = resize
        self.name_fnames = name_fnames
    #end __init__

    def reset_all(self, names_fnames, resize):
        """Resets the name to filenames and size."""
        self.pixbufs = {}
        self.name_fnames = names_fnames
        self.resize = resize
    #end reset_all

    def get(self, name):
        """Get the pixbuf with this name."""
        if name not in self.pixbufs:
            name = self.create_pixbuf(name)
        #end if
        return self.pixbufs[name]
    #end get

    def create_pixbuf(self, name):
        """Creates the image.
        Args:
          name: name of the image we are to create.
        Returns:
          The name given or EMPTY if error.
        """
        if name not in self.name_fnames:
            logging.error('Don\'t understand the name %r', name)
            return 'KEY_EMPTY'
        #end if
        ops = self.name_fnames[name]
        img = None
        for operation in ops:
            if isinstance(operation, str):
                fig = Rsvg.Handle.new_from_file(operation)
            else:
                fig = Rsvg.Handle.new_from_data(operation())
            #end if
            dims = fig.get_dimensions()
            width = round(dims.width * self.resize)
            height = round(dims.height * self.resize)
            pix = cairo.ImageSurface(cairo.Format.ARGB32, width, height)
            gc = cairo.Context(pix)
            gc.identity_matrix()
            gc.scale(self.resize, self.resize)
            gc.set_source_rgba(0, 0, 0, 0)
            gc.paint()
            fig.render_cairo(gc)
            pix.flush()
            gc = None
            img2 = Gdk.pixbuf_get_from_surface(pix, 0, 0, width, height)
            img = self._composite(img, img2)
        #end for
        self.pixbufs[name] = img
        return name
    #end create_pixbuf

    def _composite(self, img, img2):
        """Combine/layer img2 on top of img.
        Args:
          img: original image (or None).
          img2: new image to add on top.
        Returns:
          updated image.
        """
        if img:
            img2.composite \
              (
                dest = img,
                dest_x = 0,
                dest_y = 0,
                dest_width = img.props.width,
                dest_height = img.props.height,
                offset_x = 0,
                offset_y = 0,
                scale_x = 1.0,
                scale_y = 1.0,
                interp_type = GdkPixbuf.InterpType.HYPER,
                overall_alpha = 255
              )
            return img
        #end if
        return img2
    #end _composite

#end LazyPixbufCreator
