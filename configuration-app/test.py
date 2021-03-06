import gi
import dbus
import subprocess
import time
import socket

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio, GLib

class Layout:
    def getres(self):
        dsp = Gdk.Display.get_default()
        prim = dsp.get_primary_monitor()
        geo = prim.get_geometry()
        xoffset = geo.x
        yoffset = geo.y
        width = geo.width
        height = geo.height
        return (width, height, xoffset, yoffset)

    def set_panel_key(self, key, value):
        # panel keys are relocatable - so need to loop through all panels
        # and set the key to the value given

        gsettings = Gio.Settings.new('com.solus-project.budgie-panel')

        panels = gsettings.get_strv('panels')

        for panel in panels:
            gsettings = Gio.Settings.new_with_path('com.solus-project.budgie-panel.panel',
                                                   '/com/solus-project/budgie-panel/panels/{' + panel + '}/')
            if type(value) == bool:
                gsettings.set_boolean(key, value)
            elif type(value) == int:
                gsettings.set_int(key, value)
            else:
                gsettings.set_string(key, value)

    def _apply_layout(self, layout):

        # well-known name for our program
        ECHO_BUS_NAME = 'org.UbuntuBudgie.ExtrasDaemon'

        # interfaces implemented by some objects in our program
        ECHO_INTERFACE = 'org.UbuntuBudgie.ExtrasDaemon'

        # paths to some objects in our program
        ECHO_OBJECT_PATH = '/org/ubuntubudgie/extrasdaemon'

        bus = dbus.SessionBus()

        try:
            proxy = bus.get_object(ECHO_BUS_NAME, ECHO_OBJECT_PATH)
        except dbus.DBusException as e:
            # There are actually two exceptions thrown:
            # 1: org.freedesktop.DBus.Error.NameHasNoOwner
            #   (when the name is not registered by any running process)
            # 2: org.freedesktop.DBus.Error.ServiceUnknown
            #   (during auto-activation since there is no .service file)
            # TODO figure out how to suppress the activation attempt
            # also, there *has* to be a better way of managing exceptions
            if e._dbus_error_name != \
                    'org.freedesktop.DBus.Error.ServiceUnknown':
                raise
            if e.__context__._dbus_error_name != \
                    'org.freedesktop.DBus.Error.NameHasNoOwner':
                raise
            print('client: No one can hear me!!')
        else:
            iface = dbus.Interface(proxy, ECHO_INTERFACE)

            iface.ResetLayout(layout)


class CompactLayout(Layout):
    _fontname="Sawasdee "

    def _set_compact_menu(self):
        args = ['/usr/lib/budgie-desktop/arm/reset.sh', 'true']

        try:
            subprocess.run(args)
        except subprocess.CalledProcessError:
            pass

    def _set_showtime(self, timefont, datefont, linespacing):
        settings = Gio.Settings.new("org.ubuntubudgie.plugins.budgie-showtime")
        settings.set_string("timefont", timefont)
        settings.set_string("datefont", datefont)
        settings.set_int("linespacing", linespacing)

    def _set_desktopfonts(self):
        settings = Gio.Settings.new("org.gnome.desktop.wm.preferences")
        settings.set_string("titlebar-font", "Noto Sans Bold 8")

        settings = Gio.Settings.new("org.gnome.desktop.interface")
        settings.set_string("monospace-font-name", "Ubuntu Mono 10")
        settings.set_string("font-name", "Noto Sans 8")
        settings.set_string("document-font-name" , "Noto Sans 8")

        settings = Gio.Settings.new("org.nemo.desktop")
        settings.set_string("font", "Noto Sans 8")

    def _set_theme(self):
        settings = Gio.Settings.new("org.gnome.desktop.interface")
        settings.set_string("gtk-theme", "Pocillo-slim")

        settings = Gio.Settings.new("org.gnome.desktop.wm.preferences")
        settings.set_string("theme", "Pocillo-slim")

    def apply(self):
        self._set_showtime(self._fontname+"42", self._fontname+"18", -14)
        self._set_desktopfonts()
        self._set_theme()
        self._apply_layout("ubuntubudgiecompact")

        time.sleep(5)
        self.set_panel_key('autohide', 'automatic')
        self._set_compact_menu()

    def ask_to_reset(self):
        dialog = Gtk.MessageDialog(
            transient_for=window,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Reset layout to fit screen resolution?",
        )
        dialog.format_secondary_text(
            "The default layout and fonts are optimised for a standard desktop screen resolution. ......"
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.apply()
        elif response == Gtk.ResponseType.CANCEL:
            print("dialog closed by clicking CANCEL button")

        dialog.destroy()


class DefaultLayout(Layout):

    def _set_desktopfonts(self):
        settings = Gio.Settings.new("org.gnome.desktop.wm.preferences")
        settings.reset("titlebar-font")

        settings = Gio.Settings.new("org.gnome.desktop.interface")
        settings.reset("monospace-font-name")
        settings.reset("font-name")
        settings.reset("document-font-name")

        settings = Gio.Settings.new("org.nemo.desktop")
        settings.reset("font")

    def _set_showtime(self):
        settings = Gio.Settings.new("org.ubuntubudgie.plugins.budgie-showtime")
        settings.reset("timefont")
        settings.reset("datefont")
        settings.reset("linespacing")

    def _set_theme(self):
        settings = Gio.Settings.new("org.gnome.desktop.interface")
        settings.set_string("gtk-theme", "Pocillo")

        settings = Gio.Settings.new("org.gnome.desktop.wm.preferences")
        settings.set_string("theme", "Pocillo")

    def apply(self):
        self._set_desktopfonts()
        self._set_showtime()
        self._set_theme()
        self._apply_layout("ubuntubudgie")

class Overclock:
    def temp_monitor():
        cputempfile = open("/sys/class/thermal/thermal_zone0/temp")
        cpu_temp = cputempfile.read()[:2]
        cputempfile.close()
        cpuTempLabel.set_text(cpu_temp+"°C")
        return True

    def is_raspi():
        with open('/proc/cpuinfo','r') as cpufile:
            lines = cpufile.readlines()
            for line in lines:
                if "Raspberry Pi" in line:
                    return True
        return False

class Remote:
    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

class Handler:
    def on_ConfigWindow_destroy(self, *args):
        Gtk.main_quit()

    def on_CompactButton_clicked(self):
        compactlayout.apply()

    def on_DefaultButton_clicked(self):
        defaultlayout.apply()
        
    def on_RefreshIP_Clicked(self):
        iplabel.set_text(Remote.get_ip())

builder = Gtk.Builder()
builder.add_from_file("config.ui")
builder.connect_signals(Handler)

compactlayout = CompactLayout()
defaultlayout = DefaultLayout()
width, height, xoffset, yoffset = compactlayout.getres()

window = builder.get_object("ConfigWindow")

window.show_all()
logoutloginlabel = builder.get_object("LogoutLoginLabel")
logoutloginlabel.set_visible(False)

iplabel = builder.get_object("IPLabel")
Handler.on_RefreshIP_Clicked(None)

overclockgrid = builder.get_object("OverclockGrid")
cpuTempLabel = builder.get_object("cpuTempLabel")

if Overclock.is_raspi():
    GLib.timeout_add_seconds(1,Overclock.temp_monitor)
else:
    overclockgrid.set_visible(False)

if height <= 768:
    compactlayout.ask_to_reset()

Gtk.main()
