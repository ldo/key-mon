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

"""Library to get X events from Record.

This is designed to read events from X windows for keyboard and mouse
events.
"""

__author__ = 'Scott Kirkwood (scott+keymon@forusers.com)'

from Xlib import display
from Xlib import X
from Xlib import XK
from Xlib.ext import record
from Xlib.protocol import rq
import locale
import sys
import time
import threading
import collections

class XEvent:
    """An event, mimics edev.py events."""

    def __init__(self, type, scancode, code, value):
        self._type = type
        self._scancode = scancode
        self._code = code
        self._value = value
    #end __init__

    @property
    def type(self):
        "the type of the event."
        return self._type
    #end type

    @property
    def scancode(self):
        "the scancode if any."
        return self._scancode
    #end scancode

    @property
    def code(self):
        "the code string."
        return self._code
    #end code

    @property
    def value(self):
        "the value: 0 for up, 1 for down, etc."
        return self._value
    #end value

    def __repr__(self):
        return \
          (
                'XEvent(type:%s scancode:%s code:%s value:%s)'
            %
                (self._type, self._scancode, self._code, self._value)
          )
    #end __repr__

#end XEvent

class XEvents(threading.Thread):
    """A thread to queue up X window events from RECORD extension."""

    _butn_to_code = \
        {
            1: 'BTN_LEFT', 2: 'BTN_MIDDLE', 3: 'BTN_RIGHT',
            4: 'REL_WHEEL', 5: 'REL_WHEEL', 6: 'REL_LEFT', 7: 'REL_RIGHT',
        }

    def __init__(self):

        def setup_lookup():
            # sets up the key lookups.
            # set locale to default C locale, see Issue 77.
            # Use setlocale(None) to get curent locale instead of getlocal.
            # See Issue 125 and http://bugs.python.org/issue1699853.
            OLD_CTYPE = locale.setlocale(locale.LC_CTYPE, None)
            locale.setlocale(locale.LC_CTYPE, 'C')
            for name in dir(XK):
                if name[:3] == "XK_":
                    code = getattr(XK, name)
                    self.keycode_to_symbol[code] = 'KEY_' + name[3:].upper()
                #end if
            #end for
            locale.setlocale(locale.LC_CTYPE, OLD_CTYPE)
            for key, value in \
                (
                    (65027, 'KEY_ISO_LEVEL3_SHIFT'),
                    (269025062, 'KEY_BACK'),
                    (269025063, 'KEY_FORWARD'),
                    (16777215, 'KEY_CAPS_LOCK'),
                    (269025067, 'KEY_WAKEUP'),
                    # Multimedia keys
                    (269025042, 'KEY_AUDIOMUTE'),
                    (269025041, 'KEY_AUDIOLOWERVOLUME'),
                    (269025043, 'KEY_AUDIORAISEVOLUME'),
                    (269025047, 'KEY_AUDIONEXT'),
                    (269025044, 'KEY_AUDIOPLAY'),
                    (269025046, 'KEY_AUDIOPREV'),
                    (269025045, 'KEY_AUDIOSTOP'),
                    # Turkish / F layout
                    (699, 'KEY_GBREVE'), # scancode = 26 / 18
                    (697, 'KEY_IDOTLESS'), # scancode = 23 / 19
                    (442, 'KEY_SCEDILLA'), # scancode = 39 / 40
                ) \
            :
                self.keycode_to_symbol[key] = value
            #end for
        #end setup_lookup

    #begin __init__
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.setName('Xlib-thread')
        self._listening = False
        self.record_display = display.Display()
        self.local_display = display.Display()
        self.ctx = None
        self.keycode_to_symbol = collections.defaultdict(lambda: 'KEY_DUNNO')
        setup_lookup()
        self.events = []  # each of type XEvent
    #end __init__

    def run(self):
        """Standard run method for threading."""
        self.start_listening()
    #end run

    def next_event(self):
        """Returns the next event in queue, or None if none."""
        try :
            return self.events.pop(0)
        except IndexError :
            return None
        #end try
    #end next_event

    def start_listening(self):
        """Start listening to RECORD extension and queuing events."""
        if not self.record_display.has_extension("RECORD"):
            print("RECORD extension not found")
            sys.exit(1)
        #end if
        self._listening = True
        self.ctx = self.record_display.record_create_context \
          (
            0,
            [record.AllClients],
            [
                {
                    'core_requests': (0, 0),
                    'core_replies': (0, 0),
                    'ext_requests': (0, 0, 0, 0),
                    'ext_replies': (0, 0, 0, 0),
                    'delivered_events': (0, 0),
                    'device_events': (X.KeyPress, X.MotionNotify),  # why only two, it's a range?
                    'errors': (0, 0),
                    'client_started': False,
                    'client_died': False,
                }
            ]
          )

        self.record_display.record_enable_context(self.ctx, self._handler)

        # Don't understand this, how can we free the context yet still use it in Stop?
        self.record_display.record_free_context(self.ctx)
        self.record_display.close()
    #end start_listening

    def stop_listening(self):
        """Stop listening to events."""
        if not self._listening:
            return
        self.local_display.record_disable_context(self.ctx)
        self.local_display.flush()
        self.local_display.close()
        self._listening = False
        self.join(0.05)
    #end stop_listening

    def listening(self):
        """Are you listening?"""
        return self._listening
    #end listening

    def _handler(self, reply):
        # Handles an event.

        def handle_mouse(event, value):
            """Add a mouse event to events.
            Params:
              event: the event info
              value: 2=motion, 1=down, 0=up
            """
            if value == 2:
                self.events.append \
                  (
                      XEvent('EV_MOV', 0, 0, (event.root_x, event.root_y))
                  )
            elif event.detail in [4, 5]:
                if event.detail == 5:
                    value = -1
                else:
                    value = 1
                #end if
                self.events.append \
                  (
                      XEvent
                        (
                          'EV_REL',
                          0,
                          XEvents._butn_to_code.get(event.detail, 'BTN_%d' % event.detail),
                          value
                        )
                  )
            else:
                self.events.append \
                  (
                      XEvent
                        (
                          'EV_KEY',
                          0,
                          XEvents._butn_to_code.get(event.detail, 'BTN_%d' % event.detail),
                          value
                        )
                  )
            #end if
        #end handle_mouse

        def handle_key(event, value):
            """Add key event to events.
            Params:
              event: the event info
              value: 1=down, 0=up
            """
            keysym = self.local_display.keycode_to_keysym(event.detail, 0)
            if keysym not in self.keycode_to_symbol:
                print('Missing code for %d = %d' % (event.detail - 8, keysym))
            #end if
            self.events.append \
              (
                XEvent('EV_KEY', event.detail - 8, self.keycode_to_symbol[keysym], value)
              )
        #end handle_key

    #begin _handler
        if reply.category != record.FromServer:
            return
        if reply.client_swapped:
            return
        data = reply.data
        while len(data):
            event, data = rq.EventField(None).parse_binary_value \
              (
                data,
                self.record_display.display,
                None,
                None
              )
            if event.type == X.ButtonPress:
                handle_mouse(event, 1)
            elif event.type == X.ButtonRelease:
                handle_mouse(event, 0)
            elif event.type == X.KeyPress:
                handle_key(event, 1)
            elif event.type == X.KeyRelease:
                handle_key(event, 0)
            elif event.type == X.MotionNotify:
                handle_mouse(event, 2)
            else:
                print(event)
            #end if
        #end while
    #end _handler

#end XEvents

def _run_test():
    """Run a test or debug session."""
    events = XEvents()
    events.start()
    while not events.listening():
        time.sleep(1)
        print('Waiting for initializing...')
    #end while
    print('Press ESCape to quit')
    try:
        while events.listening():
            try:
                evt = events.next_event()
            except KeyboardInterrupt:
                evt = None
                print('User interrupted')
            #end try
            if evt:
                print(evt)
                if evt.code == 'KEY_ESCAPE':
                    events.stop_listening()
                #end if
            #end if
        #end while
    finally:
        events.stop_listening()
    #end try
#end _run_test

if __name__ == '__main__':
    _run_test()
#end if
