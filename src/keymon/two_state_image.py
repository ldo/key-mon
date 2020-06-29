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

"""Image that defaults back to a default state after a while.

You can switch the image to something else but it defaults back to the default
image (the first image) after calling EmptyEvent() a few times
"""

__author__ = 'scott@forusers.com (Scott Kirkwood))'

import time
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import \
    Gtk

DEFAULT_TIMEOUT_SECS = 0.5

class TwoStateImage(Gtk.Image):
    """Image has a default image (say a blank image) which it goes back to.
    It can also pass the information down to another image."""

    def __init__(self, pixbufs, normal, show=True, defer_to=None):
        Gtk.Image.__init__(self)
        self.pixbufs = pixbufs
        self.normal = normal
        self.count_down = None
        self.showit = show
        self.current = ''
        self.defer_to = defer_to
        self.timeout_secs = DEFAULT_TIMEOUT_SECS
        self.switch_to(self.normal)
        self.button_is_down = False
    #end __init__

    def reset_image(self, showit=True):
        """Image from pixbufs has changed, reset."""
        self.showit = showit
        self._switch_to(self.normal)
        self.showit = True
    #end reset_image

    @property
    def showing_button_down(self):
        "is the button currently showing the pressed state."
        return self.current != self.normal
    #end showing_button_down

    def reset_time_if_pressed(self):
        """Start the countdown now."""
        if self.showing_button_down :
            self.count_down = time.time()
        #end if
    #end reset_time_if_pressed

    def switch_to(self, name):
        """Switch to image with this name."""
        if self.current != self.normal and self.defer_to != None :
            # pass my current image settings onto defer_to button.
            self._defer_to(self.current)
            # Make sure defer_to image will only start counting timeout after self
            # image has timed out.
            if self.count_down != None :
                self.defer_to.count_down = self.count_down + self.timeout_secs
            else :
                self.defer_to.count_down += self.timeout_secs
            #end if
        #end if
        self._switch_to(name)
    #end switch_to

    def _switch_to(self, name):
        # Internal, switch to image with this name even if same.
        self.set_from_pixbuf(self.pixbufs.get(name))
        self.current = name
        self.count_down = None # stay with this image until further notice
        if self.showit :
            self.show()
        #end if
    #end _switch_to

    def switch_to_default(self):
        "starts countdown for returning to the default image."
        self.count_down = time.time()
    #end switch_to_default

    def empty_event(self):
        """Sort of a idle event.

        Returns True iff image has been changed back to normal.
        """
        changed = False
        if self.count_down != None :
            delta = time.time() - self.count_down
            if delta > self.timeout_secs :
                if (
                        self.normal.replace('_EMPTY', '') in ('SHIFT', 'ALT', 'CTRL', 'META')
                    and
                        self.button_is_down
                ) :
                    # modifier key still down, keep showing pressed image
                    pass
                else :
                    self.count_down = None
                    self._switch_to(self.normal)
                    changed = True
                #end if
            #end if
        #end if
        return changed
    #end empty_event

    def _defer_to(self, old_name):
        """If possible the button is passed on."""
        if self.defer_to != None :
            self.defer_to.switch_to(old_name)
            self.defer_to.switch_to_default()
        #end if
    #end _defer_to

#end TwoStateImage
