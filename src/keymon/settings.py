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

"""Settings dialog and related functions."""

__author__ = 'scott@forusers.com (Scott Kirkwood)'

import os
import gettext
import logging
from configparser import ConfigParser
import gi
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import \
    GObject, \
    Gtk

LOG = logging.getLogger('settings')

class SettingsDialog(Gtk.Dialog):
    """Create a settings/preferences dialog for keymon."""

    __gproperties__ = {}
    __gsignals__ = \
        {
            'settings-changed' :
                (
                    GObject.SIGNAL_RUN_LAST,
                    GObject.TYPE_NONE,
                    (),
                )
        }

    def __init__(self, unused_view, options):
        Gtk.Dialog.__init__ \
          (
            self,
            title='Preferences',
            parent=None,
            modal = True,
            destroy_with_parent = True
          ) # no more gtk.WIN_POS_MOUSE?
        self.options = options
        self.add_button(_("Close"), Gtk.ResponseType.CLOSE)
        self.set_default_size(350, 350)
        self.connect('response', self._response)
        self.notebook = Gtk.Notebook()
        self.vbox.pack_start(self.notebook, False, False, 0)

        buttons = ButtonsFrame(self)
        self.notebook.append_page(buttons, Gtk.Label(_('Buttons')))

        misc = MiscFrame(self)
        self.notebook.append_page(misc, Gtk.Label(_('Misc')))

        self.notebook.show()
        self.show()
    #end __init__

    def settings_changed(self):
        """Emit the settings changed message to parent."""
        self.emit('settings-changed')
    #end settings_changed

    def _response(self, unused_dialog, response_id):
        """Wait for the close response."""
        if response_id == Gtk.ResponseType.CLOSE:
            LOG.info('Close in _Response.')
        #end if
        self.destroy()
    #end _response

    @classmethod
    def register(cls):
        """Register this class as a Gtk widget."""
        GObject.type_register(SettingsDialog)
    #end register

#end SettingsDialog

class CommonFrame(Gtk.Frame):
    """Stuff common to several frames."""

    def __init__(self, settings):
        Gtk.Frame.__init__(self)
        self.settings = settings
        self.create_layout()
    #end __init__

    def create_layout(self):
        """Do nothing."""
        pass
    #end create_layout

    def _add_check(self, vbox, title, tooltip, option):
        """Add a check button."""
        check_button = Gtk.CheckButton(label=title)
        val = getattr(self.settings.options, option)
        logging.info('got option %s as %s', option, val)
        if val:
            check_button.set_active(True)
        else:
            check_button.set_active(False)
        #end if
        check_button.connect('toggled', self._toggled, option)
        check_button.set_tooltip_text(tooltip)
        vbox.pack_start(check_button, False, False, 0)
    #end _add_check

    def _add_dropdown(self, vbox, title, tooltip, opt_lst, option, conv, width_char=-1):
        """Add a drop down box that selects from a set of values."""
        hbox = Gtk.HBox()
        label = Gtk.Label(title)
        label.set_tooltip_text(tooltip)
        hbox.pack_start(label, expand=False, fill=False, padding=0)

        combo = Gtk.ComboBoxText()
        combo.set_wrap_width(width_char)
        for opt in opt_lst:
            combo.append_text(str(opt))
        #end for
        val = getattr(self.settings.options, option)
        try:
            index = tuple(conv(f) for f in opt_lst).index(val)
        except ValueError:
            index = 0
        #end try
        combo.set_active(index)

        combo.set_tooltip_text(tooltip)
        hbox.pack_start(combo, expand=False, fill=False, padding=10)
        logging.info('got option %s as %s', option, val)
        combo.connect('changed', self._combo_changed, option)

        vbox.pack_start(hbox, expand=False, fill=False, padding=0)
        return combo
    #end _add_dropdown

    def _toggled(self, widget, option):
      """The checkbox was toggled."""
      if widget.get_active():
          val = 1
      else:
          val = 0
      #end if
      self._update_option(option, val, str(val))
    #end _toggled

    def _combo_changed(self, widget, option):
        """The combo box changed."""
        val = widget.get_active()
        str_val = widget.get_active_text()
        self._update_option(option, val, str_val)
    #end _combo_changed

    def _update_option(self, option, val, str_val):
        """Update an option."""
        if str_val.isdigit():
            setattr(self.settings.options, option, val)
            LOG.info('Set option %s to %s' % (option, val))
        else:
            setattr(self.settings.options, option, str_val)
            LOG.info('Set option %s to %s' % (option, str_val))
        #end if
        self.settings.options.save()
        self.settings.settings_changed()
    #end _update_option

#end CommonFrame

class MiscFrame(CommonFrame):
    """The miscellaneous frame."""

    def __init__(self, settings):
        CommonFrame.__init__(self, settings)
    #end __init__

    def create_layout(self):
        """Create the box's layout."""
        vbox = Gtk.VBox()
        self._add_check \
          (
            vbox,
            _('Swap left-right mouse buttons'),
            _('Swap the left and the right mouse buttons'),
            'swap_buttons'
          )
        self._add_check \
          (
            vbox,
            _('Left+right buttons emulates middle mouse button'),
            _('Clicking both mouse buttons emulates the middle mouse button.'),
           'emulate_middle'
          )
        self._add_check \
          (
            vbox,
            _('Highly visible click'),
            _('Show a circle when the users clicks.'),
            'visible_click'
          )
        self._add_check \
          (
            vbox,
            _('Window decoration'),
            _('Show the normal windows borders'),
            'decorated'
          )
        self._add_check \
          (
            vbox,
            _('Window backgroundless'),
            _('Show only the buttons'),
            'backgroundless'
          )
        self._add_check \
          (
            vbox,
            _('Only key combinations'),
            _('Show a key only when used with a modifier key (like Control)'),
            'only_combo'
          )
        self._add_check \
          (
            vbox,
            _('StickyKeys mode'),
            _('Make modifier keys be sticky'),
            'sticky_mode'
          )

        sizes = ['1.0', '0.6', '0.8', '1.0', '1.2', '1.4', '1.6', '1.8']
        self._add_dropdown \
          (
            vbox,
            _('Scale:'),
            _(
              'How much larger or smaller than normal to make key-mon. '
              'Where 1.0 is normal sized.'
            ),
            sizes,
            'scale',
            float,
            4
          )

        timeouts = \
            [
                '0.2', '0.4', '0.5', '0.6', '0.8', '1.0', '1.2',
                '1.4', '1.6', '1.8', '2.0', '2.5', '3.0', '3.5', '4.0',
            ]
        self._add_dropdown \
          (
            vbox,
            _('Key timeout:'),
            _('How long before activated key buttons disappear. Default is 0.5'),
            timeouts,
            'key_timeout',
            float,
            4
          )
        self._add_dropdown \
          (
            vbox,
            _('Mouse timeout:'),
            _('How long before activated mouse buttons disappear. Default is 0.2'),
            timeouts,
            'mouse_timeout',
            float,
            4
          )

        self._add_dropdown \
          (
            vbox,
            _('Highly visible click timeout:'),
            _('How long before highly visible click disappear. Default is 0.2'),
            timeouts,
            'visible_click_timeout',
            float,
            4
          )

        self.themes = list(self.settings.options.themes.keys())
        self._add_dropdown \
          (
            vbox,
            _('Themes:'),
            _('Which theme of buttons to show (ex. Apple)'),
            self.themes,
            'theme',
            str
          )

        self.kbd_files = sorted \
          (
            set(os.path.basename(kbd) for kbd in self.settings.options.kbd_files)
          )
        self._add_dropdown \
          (
            vbox,
            _('Keymap:'),
            _('Which keymap file to use'),
            self.kbd_files,
            'kbd_file',
            str
          )
        self.add(vbox)
    #end create_layout

#end MiscFrame

class ButtonsFrame(CommonFrame):
    """The buttons frame."""

    def __init__(self, settings):
        """Create common frame."""
        CommonFrame.__init__(self, settings)
    #end __init__

    def create_layout(self):
        """Create the layout for buttons."""
        vbox = Gtk.VBox()

        self._add_check \
          (
            vbox,
            _('_Mouse'),
            _('Show the mouse.'),
            'mouse'
          )
        self._add_check \
          (
            vbox,
            _('_Shift'),
            _('Show the shift key when pressed.'),
            'shift'
          )
        self._add_check \
          (
            vbox,
            _('_Ctrl'),
            _('Show the Control key when pressed.'),
            'ctrl'
          )
        self._add_check \
          (
            vbox,
            _('Meta (_windows keys)'),
            _('Show the Window\'s key (meta key) when pressed.'),
            'meta'
          )
        self._add_check \
          (
            vbox,
            _('_Alt'),
            _('Show the Alt key when pressed.'),
            'alt'
          )
        self._add_dropdown \
          (
            vbox,
            _('Old Keys:'),
            _('When typing fast show more than one key typed.'),
            [0, 1, 2, 3, 4],
            'old_keys',
            int
          )

        fadeouts = ['0', '0.5', '1.0', '1.5', '2.0', '3.0', '4.0', '5.0']
        self._add_dropdown \
          (
            vbox,
            _('Fade window after period (seconds).'),
            _('How long before window disappears after a click in seconds.'),
            fadeouts,
            'no_press_fadeout',
            float,
            20
          )

        self.add(vbox)
    #end create_layout

#end ButtonsFrame

def _test_settings_changed(unused_widget):
    """Help to test if the settings change message is received."""
    print('Settings changed')
#end _test_settings_changed

def manually_run_dialog():
    """Test the dialog without starting keymon."""
    import key_mon

    SettingsDialog.register()
    gettext.install('key_mon', 'locale')
    logging.basicConfig \
      (
        level=logging.DEBUG,
        format = '%(filename)s [%(lineno)d]: %(levelname)s %(message)s'
      )
    options = key_mon.create_options()
    options.read_ini_file('~/.config/key-mon/config')
    dlg = SettingsDialog(None, options)
    dlg.connect('settings-changed', _test_settings_changed)
    dlg.show_all()
    dlg.run()
    return 0
#end manually_run_dialog

def get_config_dir():
    """Return the base directory of configuration."""
    return \
      (
            os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        +
            '/key-mon'
      )
#end get_config_dir

def get_config_dirs(kind):
    """Return search paths of certain kind of configuration directory.
    Args:
      kind: Subfolder name
    Return:
      List of full paths
    """
    config_dirs = \
        [
            d
                for d in
                    (
                        os.path.join(get_config_dir(), kind),
                        os.path.join(os.path.dirname(os.path.abspath(__file__)), kind)
                    )
            if os.path.exists(d)
        ]
    return config_dirs
#end get_config_dirs

def get_themes():
    """Return a dict of themes.
      keys are theme names
      values are tuples of (description, path)
        path is where the theme directory located,
        i.e. theme files are path/*.
    """
    theme_dirs = get_config_dirs('themes')
    themes = {}
    for theme_dir in theme_dirs:
        for entry in sorted(os.listdir(theme_dir)):
            try:
                parser = ConfigParser()
                theme_config = os.path.join(theme_dir, entry, 'config')
                parser.read(theme_config)
                desc = parser.get('theme', 'description')
                if entry not in themes:
                    themes[entry] = (desc, os.path.join(theme_dir, entry))
                #end if
            except:
                LOG.warning(_('Unable to read theme %r') % (theme_config))
            #end try
        #end for
    #end for
    return themes
#end get_themes

def get_kbd_files():
    """Return a list of kbd file paths"""
    config_dirs = get_config_dirs('')
    kbd_files = [
        os.path.join(d, f) \
        for d in config_dirs \
        for f in sorted(os.listdir(d)) if f.endswith('.kbd')]
    return kbd_files
#end get_kbd_files

if __name__ == '__main__':
    manually_run_dialog()
#end if
