#!/usr/bin/python
#
# Copyright 2009 Scott Kirkwood. All Rights Reserved.

"""Create pixbuf on demand.

This creates a gtk pixbuf in one of 2 manners:
1) Simple filename (probably supports most image formats)
2) A function which returns bytes to a file which can be read by
   pixbuf_new_from_file().

The name_fnames contains a list for key.  Each element of the list will be
composted with the previous element (overlayed on top of).

Alpha transparencies from the new, overlayed, image are respected.
"""

__author__ = 'scott@forusers.com (Scott Kirkwood))'

import pygtk
pygtk.require('2.0')
import gtk
import logging
import os
import tempfile
import types

class LazyPixbufCreator():
  """Class to create SVG images on the fly."""
  def __init__(self, name_fnames):
    """Initialize with empty.

    Args:
      name_fnames: List of names to filename list.
    """
    self.pixbufs = {}
    self.name_fnames = name_fnames

  def Get(self, name):
    if name not in self.pixbufs:
      name = self.CreatePixbuf(name)
    return self.pixbufs[name]

  def CreatePixbuf(self, name):
    """Creates the image.
    Args:
      name: name of the image we are to create.
    Returns:
      The name given or EMPTY if error.
    """
    if name not in self.name_fnames:
      logging.error('Don\'t understand the name %r' % name)
      return 'KEY_UP_EMPTY'
    ops = self.name_fnames[name]
    img = None
    for op in ops:
      if isinstance(op, types.StringTypes):
        img = self.Composite(img, gtk.gdk.pixbuf_new_from_file(op))
      else:
        bytes = op()
        f = tempfile.NamedTemporaryFile(mode='w', prefix='keymon-')
        f.write(bytes)
        f.flush()
        img = self.Composite(img, gtk.gdk.pixbuf_new_from_file(f.name))
        f.close()
        try:
          os.unlink(f.name)
        except OSError:
          pass
    self.pixbufs[name] = img
    return name

  def Composite(self, img, img2):
    """Combine/layer img2 on top of img.
    Args:
      img: original image (or None).
      img2: new image to add on top.
    Returns:
      updated image.
    """
    if img:
      img2.composite(img,
          0, 0, img.props.width, img.props.height,  # x, y, w, h
          0, 0,  # offset x, y
          1.0, 1.0,  # scale x, y
          gtk.gdk.INTERP_HYPER, 255)  # interpolation type, alpha
      return img
    return img2
