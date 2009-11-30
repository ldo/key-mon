#!/usr/bin/python
#
# Copyright 2009 Scott Kirkwood. All Rights Reserved.

"""Keyboard Status Monitor.
Monitors one or more keyboards and mouses.
Shows their status graphically.
"""

__author__ = 'scott@forusers.com (scottkirkwood))'

import pygtk
pygtk.require('2.0')
import gobject
import gtk
import logging
import os
import sys

import evdev
import lazy_pixbuf_creator
import mod_mapper
import two_state_image
try:
  import dbus
except:
  print "Unable to import dbus interface, quitting"
  sys.exit(-1)

def FixSvgKeyClosure(fname, from_tos):
  """Create a closure to modify the key.
  Args:
    from_tos: list of from, to pairs for search replace.
  Returns:
    A bound function which returns the file fname with modifications.
  """

  def FixSvgKey():
    """Given an SVG file return the SVG text fixed."""
    f = open(fname)
    bytes = f.read()
    f.close()
    for f, t in from_tos:
      bytes = bytes.replace(f, t)
    return bytes

  return FixSvgKey

class KeyMon:
  def __init__(self, scale, meta, kbd_file, emulate_middle):
    """Create the Key Mon window.
    Args:
      scale: float 1.0 is default which means normal size.
      meta: boolean show the meta (windows key)
      kbd_file: string Use the kbd file given.
      emulate_middle: Emulate the middle mouse button.
    """
    self.pathname = os.path.dirname(sys.argv[0])
    self.scale = scale
    if scale < 1.0:
      self.svg_size = '-small'
    else:
      self.svg_size = ''
    self.enabled = {
        'MOUSE': True,
        'META': meta,
    }
    self.emulate_middle = emulate_middle
    self.modmap = mod_mapper.SafelyReadModMap(kbd_file)

    bus = dbus.SystemBus()
    hal_obj = bus.get_object ("org.freedesktop.Hal", "/org/freedesktop/Hal/Manager")
    hal = dbus.Interface(hal_obj, "org.freedesktop.Hal.Manager")
    self.GetKeyboardDevices(bus, hal)
    self.GetMouseDevices(bus, hal)
    self.name_fnames = self.CreateNamesToFnames()
    self.pixbufs = lazy_pixbuf_creator.LazyPixbufCreator(self.name_fnames, self.scale)
    self.CreateWindow()

  def CreateNamesToFnames(self):
    ftn = {
      'MOUSE': [self.SvgFname('mouse'),],
      'BTN_LEFT': [self.SvgFname('mouse'), self.SvgFname('left-mouse')],
      'BTN_RIGHT': [self.SvgFname('mouse'), self.SvgFname('right-mouse')],
      'BTN_MIDDLE': [self.SvgFname('mouse'), self.SvgFname('middle-mouse')],
      'SCROLL_UP': [self.SvgFname('mouse'), self.SvgFname('scroll-up-mouse')],
      'SCROLL_DOWN': [self.SvgFname('mouse'), self.SvgFname('scroll-dn-mouse')],

      'SHIFT': [self.SvgFname('shift')],
      'SHIFT_EMPTY': [self.SvgFname('shift'), self.SvgFname('whiteout-72')],
      'CTRL': [
          FixSvgKeyClosure(self.SvgFname('alt'), [('Alt', 'Ctrl')])],
      'CTRL_EMPTY': [
          FixSvgKeyClosure(self.SvgFname('alt'), [('Alt', 'Ctrl')]), self.SvgFname('whiteout-58')],
      'META': [
          FixSvgKeyClosure(self.SvgFname('alt'), [('Alt', '')]), self.SvgFname('meta')],
      'META_EMPTY': [
          FixSvgKeyClosure(self.SvgFname('alt'), [('Alt', '')]), 
              self.SvgFname('meta'), self.SvgFname('whiteout-58')],
      'ALT': [self.SvgFname('alt')],
      'ALT_EMPTY': [self.SvgFname('alt'), self.SvgFname('whiteout-58')],
      'KEY_EMPTY': [
          FixSvgKeyClosure(self.SvgFname('one-char-template'), [('&amp;', '')]), 
              self.SvgFname('whiteout-48')],
    }
    if self.scale >= 1.0:
      ftn.update({
        'KEY_SPACE': [
            FixSvgKeyClosure(self.SvgFname('two-line-wide'), [('TOP', 'Space'), ('BOTTOM', '')])],
        'KEY_TAB': [
            FixSvgKeyClosure(self.SvgFname('two-line-wide'), [('TOP', 'Tab'), ('BOTTOM', u'\u21B9')])],
        'KEY_BACKSPACE': [
            FixSvgKeyClosure(self.SvgFname('two-line-wide'), [('TOP', 'Back'), ('BOTTOM', u'\u21fd')])],
        'KEY_RETURN': [
            FixSvgKeyClosure(self.SvgFname('two-line-wide'), [('TOP', 'Enter'), ('BOTTOM', u'\u23CE')])],
      })
    else:
      ftn.update({
        'KEY_SPACE': [
            FixSvgKeyClosure(self.SvgFname('one-line-wide'), [('&amp;', 'Space')])],
        'KEY_TAB': [
            FixSvgKeyClosure(self.SvgFname('one-line-wide'), [('&amp;', 'Tab')])],
        'KEY_BACKSPACE': [
            FixSvgKeyClosure(self.SvgFname('one-line-wide'), [('&amp;', 'Back')])],
        'KEY_RETURN': [
            FixSvgKeyClosure(self.SvgFname('one-line-wide'), [('&amp;', 'Enter')])],
      })
    return ftn

  def CreateWindow(self):
    self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)

    self.window.set_title('Keyboard Status Monitor')
    width, height = 308 * self.scale, 48 * self.scale
    self.window.set_default_size(int(width), int(height))
    self.window.set_decorated(False)
    self.window.set_opacity(0.1)
    self.window.set_keep_above(True)

    self.event_box = gtk.EventBox()
    self.window.add(self.event_box)
    self.event_box.show()

    self.hbox = gtk.HBox(False, 0)
    self.event_box.add(self.hbox)

    self.mouse_image = two_state_image.TwoStateImage(self.pixbufs, 'MOUSE')
    self.hbox.pack_start(self.mouse_image, False, False, 0)
    if not self.enabled['MOUSE']:
      self.mouse_image.hide()
    self.shift_image = two_state_image.TwoStateImage(self.pixbufs, 'SHIFT_EMPTY')
    self.hbox.pack_start(self.shift_image, False, False, 0)
    self.ctrl_image = two_state_image.TwoStateImage(self.pixbufs, 'CTRL_EMPTY')
    self.hbox.pack_start(self.ctrl_image, False, False, 0)
    self.meta_image = two_state_image.TwoStateImage(self.pixbufs, 'META_EMPTY',
        self.enabled['META'])
    if not self.enabled['META']:
      self.meta_image.hide()
    self.hbox.pack_start(self.meta_image, False, False, 0)
    self.alt_image = two_state_image.TwoStateImage(self.pixbufs, 'ALT_EMPTY')
    self.hbox.pack_start(self.alt_image, False, False, 0)
    self.key_image = two_state_image.TwoStateImage(self.pixbufs, 'KEY_EMPTY')
    self.hbox.pack_start(self.key_image, True, True, 0)

    self.buttons = [self.mouse_image, self.shift_image, self.ctrl_image,
        self.meta_image, self.alt_image, self.key_image]

    self.hbox.show()
    self.AddEvents()

    self.window.show()

  def SvgFname(self, fname):
    fullname = os.path.join(self.pathname, 'svg/%s%s.svg' % (fname, self.svg_size))
    if self.svg_size and not os.path.exists(fullname):
      # Small not found, defaulting to large size
      fullname = 'svg/%s.svg' % fname
    return fullname

  def AddEvents(self):
    self.window.connect('destroy', self.Destroy)
    self.window.connect('button-press-event', self.ButtonPressed)
    self.event_box.connect('button_release_event', self.RightClickHandler)

    try:
      self.devices = evdev.DeviceGroup(self.keyboard_filenames +
                                       self.mouse_filenames)
    except OSError, e:
      logging.exception(e)
      if str(e) == 'Permission denied':
        gksudo()
      print
      print 'You may need to run this as %r' % 'sudo %s' % sys.argv[0]
      sys.exit(-1)

    accelgroup = gtk.AccelGroup()
    key, modifier = gtk.accelerator_parse('<Control>q')
    accelgroup.connect_group(key, modifier, gtk.ACCEL_VISIBLE, self.Quit)
    self.window.add_accel_group(accelgroup)
    
    gobject.idle_add(self.OnIdle)

  def ButtonPressed(self, widget, evt):
    if evt.button != 1:
      return True
    widget.begin_move_drag(evt.button, int(evt.x_root), int(evt.y_root), evt.time)
    return True

  def OnIdle(self):
    event = self.devices.next_event()
    self.HandleEvent(event)
    return True  # continue calling

  def HandleEvent(self, event):
    if not event:
      for button in self.buttons:
        button.EmptyEvent()
      return
    if event.type == "EV_KEY" and event.value in (0, 1):
      if event.code.startswith("KEY"):
        code_num = event.codeMaps[event.type].toNumber(event.code)
        self.HandleKey(code_num, event.value)
      elif event.code.startswith("BTN"):
        self.HandleMouseButton(event.code, event.value)
    elif event.type.startswith("EV_REL") and event.code == 'REL_WHEEL':
      self.HandleMouseScroll(event.value, event.value)

  def _HandleEvent(self, image, name, code):
    if code == 1:
      image.SwitchTo(name)
    else:
      image.SwitchToDefault()

  def HandleKey(self, scan_code, value):
    if scan_code in self.modmap:
      code, medium_name, short_name = self.modmap[scan_code]
    else:
      print 'No mapping for scan_code %d' % scan_code
      return
    if self.scale < 1.0 and short_name:
      medium_name = short_name
    # print 'Key %s pressed = %r' % (code, medium_name)
    if code in self.name_fnames:
      self._HandleEvent(self.key_image, code, value)
      return
    if code.startswith('KEY_SHIFT'):
      self._HandleEvent(self.shift_image, 'SHIFT', value)
      return
    if code.startswith('KEY_ALT') or code == 'KEY_ISO_LEVEL3_SHIFT':
      self._HandleEvent(self.alt_image, 'ALT', value)
      return
    if code.startswith('KEY_CONTROL'):
      self._HandleEvent(self.ctrl_image, 'CTRL', value)
      return
    if code.startswith('KEY_SUPER') or code == 'KEY_MULTI_KEY':
      if self.enabled['META']:
        self._HandleEvent(self.meta_image, 'META', value)
      return
    if code.startswith('KEY_KP'):
      letter = medium_name
      if code not in self.name_fnames:
        template = 'one-char-numpad-template'
        self.name_fnames[code] = [
            FixSvgKeyClosure(self.SvgFname(template), [('&amp;', letter)])]
      self._HandleEvent(self.key_image, code, value)
      return
    if code.startswith('KEY_'):
      letter = medium_name
      if code not in self.name_fnames:
        if len(letter) == 1:
          template = 'one-char-template'
        else:
          template = 'multi-char-template'
        self.name_fnames[code] = [
            FixSvgKeyClosure(self.SvgFname(template), [('&amp;', letter)])]
      self._HandleEvent(self.key_image, code, value)
      return

  def HandleMouseButton(self, code, value):
    if self.enabled['MOUSE']:
      if self.emulate_middle and ((self.mouse_image.current == 'BTN_LEFT' and code == 'BTN_RIGHT') or
         (self.mouse_image.current == 'BTN_RIGHT' and code == 'BTN_LEFT')):
        code = 'BTN_MIDDLE'
      self._HandleEvent(self.mouse_image, code, value)
    return True

  def HandleMouseScroll(self, dir, value):
    if dir > 0:
      self._HandleEvent(self.mouse_image, 'SCROLL_UP', 1)
    elif dir < 0:
      self._HandleEvent(self.mouse_image, 'SCROLL_DOWN', 1)
    self.mouse_image.SwitchToDefault()
    return True

  def Quit(self, *args):
    self.Destroy(None)

  def Destroy(self, widget, data=None):
    gtk.main_quit()

  def RightClickHandler(self, widget, event):
    if event.button != 3:
      return

    menu = self.CreateContextMenu()

    menu.show()
    menu.popup(None, None, None, event.button, event.time)

  def CreateContextMenu(self):
    menu = gtk.Menu()

    toggle_chrome = gtk.CheckMenuItem('Window _Chrome')
    toggle_chrome.set_active(self.window.get_decorated())
    toggle_chrome.connect_object('activate', self.ToggleChrome,
       self.window.get_decorated())
    toggle_chrome.show()
    menu.append(toggle_chrome)

    toggle_mouse = gtk.CheckMenuItem('Mouse')
    visible = self.mouse_image.flags() & gtk.VISIBLE
    toggle_mouse.set_active(visible)
    toggle_mouse.connect_object('activate', self.ToggleMouse,
        visible)
    toggle_mouse.show()
    menu.append(toggle_mouse)

    toggle_metakey = gtk.CheckMenuItem('Meta Key')
    visible = self.meta_image.flags() & gtk.VISIBLE
    toggle_metakey.set_active(visible)
    toggle_metakey.connect_object('activate', self.ToggleMetaKey,
        visible)
    toggle_metakey.show()
    menu.append(toggle_metakey)

    quit = gtk.MenuItem('_Quit\tCtrl-Q')
    quit.connect_object('activate', self.Destroy, None)
    quit.show()

    menu.append(quit)
    return menu

  def ToggleChrome(self, current):
    self.window.set_decorated(not current)

  def ToggleMetaKey(self, current):
    self._ToggleAKey(self.meta_image, 'META', current)

  def ToggleMouse(self, current):
    self._ToggleAKey(self.mouse_image, 'MOUSE', current)

  def _ToggleAKey(self, image, name, current):
    if current:
      image.showit = False
      self.enabled[name] = False
      image.hide()
    else:
      image.showit = True
      self.enabled[name] = True
      image.SwitchToDefault()

  def GetKeyboardDevices(self, bus, hal):
    self.keyboard_devices = hal.FindDeviceByCapability("input.keyboard")
    if not self.keyboard_devices:
      print "No keyboard devices found"
      sys.exit(-1)

    self.keyboard_filenames = []
    for keyboard_device in self.keyboard_devices:
      dev_obj = bus.get_object ("org.freedesktop.Hal", keyboard_device)
      dev = dbus.Interface (dev_obj, "org.freedesktop.Hal.Device")
      self.keyboard_filenames.append(dev.GetProperty("input.device"))

  def GetMouseDevices(self, bus, hal):
    self.mouse_devices = hal.FindDeviceByCapability ("input.mouse")
    if not self.mouse_devices:
      print "No mouse devices found"
      sys.exit(-1)
    self.mouse_filenames = []
    for mouse_device in self.mouse_devices:
      dev_obj = bus.get_object ("org.freedesktop.Hal", mouse_device)
      dev = dbus.Interface (dev_obj, "org.freedesktop.Hal.Device")
      self.mouse_filenames.append(dev.GetProperty("input.device"))


if __name__ == "__main__":
  import optparse
  parser = optparse.OptionParser()
  parser.add_option('-s', '--smaller', dest='smaller', default=False, action='store_true',
                    help='Make the dialog 25% smaller than normal.')
  parser.add_option('-l', '--larger', dest='larger', default=False, action='store_true',
                    help='Make the dialog 25% larger than normal.')
  parser.add_option('-m', '--meta', dest='meta', action='store_true',
                    help='Show the meta (windows) key.')
  parser.add_option('--scale', dest='scale', default=1.0, type='float',
                    help='Scale the dialog. ex. 2.0 is 2 times larger, 0.5 is half the size.')
  parser.add_option('--kbdfile', dest='kbd_file', default=None,
                    help='Use this kbd filename instead running xmodmap.')
  parser.add_option('--emulate-middle', dest='emulate_middle', action="store_true",
                    help=('If you presse the left, and right mouse buttons at the same time, '
                          'show it as a middle mouse button. '))
  scale = 1.0
  (options, args) = parser.parse_args()
  if options.smaller:
    scale = 0.75
  elif options.larger:
    scale = 1.25
  elif options.scale:
    scale = options.scale
  keymon = KeyMon(scale, options.meta, options.kbd_file, options.emulate_middle)
  gtk.main()
