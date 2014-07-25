#   Configurable notification daemon written in python featuring queues and history display
#   Copyright (C) 2014  Juan Manuel Schillaci
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software Foundation,
#   Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
#   django-remote-scneario version 0.1, Copyright (C) 2014  Juan Manuel Schillaci
#   django-remote-scenario comes with ABSOLUTELY NO WARRANTY.
#   This is free software, and you are welcome to redistribute it
#   under certain conditions;

##################################################################################################
##################################################################################################
##################################################################################################
##################################################################################################
#Important, credit where its due!: This file has been forked from https://github.com/the-isz/notipy
##################################################################################################
##################################################################################################
##################################################################################################
##################################################################################################

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import collections
import itertools
import io
import logging
import os.path
import urllib
import warnings

import dbus.mainloop.glib
import dbus.service
import dbus
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk, Gdk, GdkPixbuf, Pango


UNREAD_FILE = "/tmp/unread_notifications"


class LayoutAnchor(object):
    NORTH_WEST, SOUTH_WEST, SOUTH_EAST, NORTH_EAST = range(4)


class LayoutDirection(object):
    VERTICAL, HORIZONTAL = range(2)


class Layout(object):
    @staticmethod
    def layout_north_west(margins, windows, direction):
        base = (margins[3], margins[0])

        for win in windows.itervalues():
            win.move(base[0], base[1])
            if direction == LayoutDirection.VERTICAL:
                base = (base[0], base[1] + win.get_size()[1])
            else:
                base = (base[0] + win.get_size()[0], base[1])

    @staticmethod
    def layout_south_west(margins, windows, direction):
        base = (margins[3], Gdk.Screen.height() - margins[2])

        for win in windows.itervalues():
            win.move(base[0], base[1] - win.get_size()[1])
            if direction == LayoutDirection.VERTICAL:
                base = (base[0], base[1] - win.get_size()[1])
            else:
                base = (base[0] + win.get_size()[0], base[1])

    @staticmethod
    def layout_south_east(margins, windows, direction):
        base = (Gdk.Screen.width() - margins[1],
            Gdk.Screen.height() - margins[2])

        for win in windows.itervalues():
            win.move(base[0] - win.get_size()[0], base[1] - win.get_size()[1])
            if direction == LayoutDirection.VERTICAL:
                base = (base[0], base[1] - win.get_size()[1])
            else:
                base = (base[0] - win.get_size()[0], base[1])

    @staticmethod
    def layout_north_east(margins, windows, direction):
        base = (Gdk.Screen.width() - margins[1], margins[0])

        for win in windows.itervalues():
            win.move(base[0] - win.get_size()[0], base[1])
            if direction == LayoutDirection.VERTICAL:
                base = (base[0], base[1] + win.get_size()[1])
            else:
                base = (base[0] - win.get_size()[0], base[1])


class NotificationDaemon(dbus.service.Object):
    """
    Implements the gnome Desktop Notification Specification [1] to display
    popup information.

    [1] http://developer.gnome.org/notification-spec/
    """

    def __init__(self, objectPath):
        bus_name = dbus.service.BusName(
            "org.freedesktop.Notifications", dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, objectPath)

        self._lastID = 0
        self._windows = collections.OrderedDict()
        self._closeEvents = {}
        self.max_expire_timeout = 10000
        self.margins = [0 for x in range(4)]
        self.layoutAnchor = LayoutAnchor.NORTH_WEST
        self.layoutDirection = LayoutDirection.VERTICAL
        self.reset_counter_file()

    def set_max_expire_timeout(self, max_expire_timeout):
        if max_expire_timeout < 1:
            warnings.warn("Ignoring max_expire_timeout value < 1.")
            return
        self._max_expire_timeout = max_expire_timeout

    def max_expire_timeout(self):
        return self._max_expire_timeout

    max_expire_timeout = property(max_expire_timeout, set_max_expire_timeout, \
        doc="Maximum time for notifications to be shown in [ms]. "
            "Default: 10000.")

    def set_margins(self, margins):
        try:
            newMargins = [int(x) for x in itertools.islice(margins, 4)]
            self._margins = newMargins
        except ValueError:
            warnings.warn(
                    "Ignoring margins value because not all values could be "
                    "converted to integer values.")
        except TypeError:
            warnings.warn("Ignoring margins value because it is not "
                          "subscriptable.")
        except IndexError:
            warnings.warn("Ignoring margins value because it doesn't have "
                          "enough values.")

    def margins(self):
        return self._margins

    margins = property(margins, set_margins,
        doc="Margins for top, right, bottom and left side of the screen.")

    def set_layout_anchor(self, layoutAnchor):
        try:
            self._layoutAnchorFunc = \
                {
                    LayoutAnchor.NORTH_WEST: Layout.layout_north_west,
                    LayoutAnchor.SOUTH_WEST: Layout.layout_south_west,
                    LayoutAnchor.SOUTH_EAST: Layout.layout_south_east,
                    LayoutAnchor.NORTH_EAST: Layout.layout_north_east,
                }[layoutAnchor]
        except KeyError:
            warnings.warn("Ignoring invalid layoutAnchor setting.")
            return

        self._layoutAnchor = layoutAnchor

    def layout_anchor(self):
        return self._layoutAnchor

    layoutAnchor = property(layout_anchor, set_layout_anchor,
        doc="Layout origin for the notification windows.")

    def set_layout_direction(self, layoutDirection):
        if layoutDirection not in \
            [LayoutDirection.VERTICAL, LayoutDirection.HORIZONTAL]:
            warnings.warn("Ignoring invalid layoutDirection setting.")
            return

        self._layoutDirection = layoutDirection

    def layout_direction(self):
        return self._layoutDirection

    layoutDirection = property(layout_direction, set_layout_direction,
        doc="Layout direction for the notification windows.")

    def _update_layout(self):
        """
        Recalculates the layout of all notification windows.
        """
        self._layoutAnchorFunc(
            self.margins, self._windows, self.layoutDirection)

    def matches_rules(self, summary, body):
        return True

    def reset_counter_file(self):
        try:
            fp = io.open(UNREAD_FILE, "w")
            fp.write(u"0")
            fp.close()
        except:
            pass

    def get_counter_value(self):
        try:
            fp = io.open(UNREAD_FILE, "r")
            unread_messages = int(fp.readline())
            fp.close()
        except:
            unread_messages = 0

        return unread_messages

    def increase_counter_file(self):
        try:
            unread = self.get_counter_value()
            fp = io.open(UNREAD_FILE, "w")
            fp.write(unicode(unread+1))
            fp.close()
        except:
            pass

    def _create_win(self, summary, body, icon=None):
        win = Gtk.Window(type=Gtk.WindowType.POPUP)

        frame = Gtk.Frame()
        win.add(frame)

        hBox = Gtk.HBox()
        frame.add(hBox)

        logging.debug("type of icon: {}".format(str(type(icon))))

        iconWidget = None

        if not icon is None:
            if isinstance(icon, unicode):
                icon_path = os.path.expanduser(urllib.url2pathname(icon))
                if os.path.isfile(icon_path):
                    iconWidget = Gtk.Image()
                    iconWidget.set_from_file(icon_path)
                else:
                    # Note:
                    # See output of following script for available names:
                    # from gi.repository import Gtk
                    # print("\n".join(
                    #     Gtk.IconTheme.get_default().list_icons(None)))
                    theme = Gtk.IconTheme.get_default()
                    if theme.has_icon(icon):
                        iconWidget = Gtk.Image()
                        iconWidget.set_from_icon_name(icon, Gtk.IconSize.DND)
                    else:
                        warnings.warn(
                            "\"{}\" seems to be neither a valid icon file nor "
                            "a name in a freedesktop.org-compliant icon theme "
                            "(or your theme doesn't have that name). Ignoring."
                            .format(icon))

            else:
                # For image-data and icon_data, image should look like this:
                #
                # dbus.Struct(
                #   (dbus.Int32,                   # width
                #    dbus.Int32,                   # height
                #    dbus.Int32,                   # rowstride
                #    dbus.Boolean,                 # has alpha
                #    dbus.Int32,                   # bits per sample
                #    dbus.Int32,                   # channels
                #    dbus.Array([dbus.Byte, ...])) # image data
                # )

                # data, colorspace, has_alpha, bits_per_sample, width, height,
                # rowstride, destroy_fn, destroy_fn_data
                # FIXME: Do I need to free the image via a function callback?
                pixbuf = GdkPixbuf.Pixbuf.new_from_data(
                    bytearray(icon[6]), GdkPixbuf.Colorspace.RGB, icon[3],
                    icon[4], icon[0], icon[1], icon[2],
                    lambda x, y: None, None)

                iconWidget = Gtk.Image()
                iconWidget.set_from_pixbuf(pixbuf)

        if not iconWidget is None:
            hBox.pack_start(iconWidget, False, False, 0)

        vBox = Gtk.VBox()
        hBox.pack_start(vBox, False, False, 0)


        def set_label_contents(l, s):
            try:
                # Parameters: markup_text, length, accel_marker
                # Return: (success, attr_list, text, accel_char)
                parse_result = Pango.parse_markup(s, -1, u"\x00")
                l.set_text(parse_result[2])
                l.set_attributes(parse_result[1])
            except GLib.GError:
                logging.exception("Invalid pango markup.")
                l.set_text(s)


        if self.matches_rules(summary, body):
            # Temporary rule, this should be match from a config file
            summary_text = summary.__str__()
            if summary_text.find('New message')!='-1':
                self.increase_counter_file()

        summaryLabel = Gtk.Label()
        set_label_contents(summaryLabel, summary)
        vBox.pack_start(summaryLabel, False, False, 0)

        separator = Gtk.HSeparator()
        vBox.pack_start(separator, False, False, 0)

        bodyLabel = Gtk.Label()
        set_label_contents(bodyLabel, body)
        vBox.pack_start(bodyLabel, False, False, 0)

        # The window's size has default values before showing it.
        win.show_all()

        return win

    def _notification_expired(self, id):
        """
        Callback called when a notification expired.

        @param id: the ID of the notification.
        @returns: False
        """
        self._close_notification(id, 1)
        return False  # Don't repeat timeout

    def _window_clicked(self, widget, event, id):
        self._close_notification(id, 2)

    def _remove_close_event(self, id):
        """
        Removes the close event belonging to the notification with ID id.

        @param id: the ID of the notification whose close event is to be
                   removed.
        @return: True if a close event was removed, False otherwise.
        """
        if id not in self._closeEvents:
            return False

        closeEvent = self._closeEvents.pop(id)
        GLib.source_remove(closeEvent)
        return True

    def _remove_window(self, id, removeFromDict=True):
        """
        Removes the window belonging to the notification with ID id.

        @param id: the ID of the notification whose window is to be removed.
        @param removeFromDict: if True, id will be erased from self._windows
        @return: True if a window was removed, False otherwise.
        """
        if id not in self._windows:
            return False

        win = self._windows[id]
        win.hide()
        win.destroy()

        if removeFromDict:
            del self._windows[id]

        return True

    def _close_notification(self, id, reason):
        """
        Closes a notification and emits NotificationClosed if the notification
        exists.

        @param id: the ID of the notification.
        @param reason: the reason for closing the notification.
        @returns: True if a notification with this id existed, False otherwise.
        """
        self._remove_close_event(id)

        if self._remove_window(id):
            self._update_layout()
            self.NotificationClosed(id, reason)
            return True
        else:
            warnings.warn("Attempt to close non-existent notification {}"
                .format(id))
            return False

    @dbus.service.method(
        dbus_interface="org.freedesktop.Notifications",
        in_signature="",
        out_signature="as")
    def GetCapabilities(self):
        """
        Get the capabilities of this notification daemon implementation.
        @returns: An array of strings
        """
        # Available capabilities:
        # action-icons actions body body-hyperlinks body-images body-markup
        # icon-multi icon-static persistence sound
        return ["body", "body-markup", "persistence", "icon-static"]

    @dbus.service.method(
        dbus_interface="org.freedesktop.Notifications",
        in_signature="susssava{sv}i",
        out_signature="u")
    def Notify(
        self, app_name, replaces_id, app_icon, summary,
        body, actions, hints, expire_timeout):
        """
        @param app_name: string
        @param replaces_id: unsigned int
        @param app_icon: string
        @param summary: string
        @param body: string
        @param actions: array (even: id (int), odd: localized string)
        @param hints: dict
        @param expire_timeout: int

        @returns: unsigned int
        """
        notificationID = 0

        if 0 != replaces_id:
            # We can't use _close_notification here because
            # a) the NotificationClosed signal must not be emitted
            # b) we must not remove replaces_id from _windows or the order of
            #    the values in the dict would be changed
            # c) that would cause _update_layout to be called twice
            self._remove_close_event(replaces_id)
            self._remove_window(replaces_id, False)
            notificationID = replaces_id
        else:
            self._lastID += 1
            notificationID = self._lastID

        logging.debug("summary: \"{}\", body: \"{}\"".format(
            unicode(summary).encode("ascii", errors="backslashreplace"),
            unicode(body).encode("ascii", errors="backslashreplace")))
        logging.debug("Notification ID: {}".format(notificationID))

        try:
            # Priorities for icon sources:
            #
            # 1. image-data: hint. raw image data structure of signature
            #                (iiibiiay)
            # 2. image-path: hint. either an URI (file://...) or a name in a
            #                freedesktop.org-compliant icon theme
            # 3. app_icon:   parameter. same as image-path
            # 4. icon_data:  hint. same as image-data

            image = None

            if "image-data" in hints:
                image = hints["image-data"]
            elif "image-path" in hints:
                image = hints["image-path"]
            elif app_icon != "":
                image = app_icon
            elif "icon_data" in hints:
                image = hints["icon_data"]

            win = self._create_win(summary, body, image)
            win.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            win.connect(
                "button-press-event", self._window_clicked, notificationID)
            self._windows[notificationID] = win
            self._update_layout()

            if 0 != expire_timeout:
                timeout = \
                    (self.max_expire_timeout if expire_timeout < 0 else \
                    min(expire_timeout, self.max_expire_timeout)) / 1000

                logging.debug("Will close notification {} after {} seconds."
                    .format(notificationID, timeout))

                self._closeEvents[notificationID] = \
                    GLib.timeout_add_seconds(
                        timeout,
                        self._notification_expired,
                        notificationID)

        except Exception as e:
            logging.exception("Exception occured during window creation.")

        return notificationID

    @dbus.service.method(
        dbus_interface="org.freedesktop.Notifications",
        in_signature="u",
        out_signature="")
    def CloseNotification(self, id):
        """
        NotificationClosed signal or empty D-BUS error
        @param id: unsigned int
        """
        if not self._close_notification(id, 3):
            # Don't know what sending back an empty D-BUS error message is
            # supposed to mean...
            pass

    @dbus.service.method(
        dbus_interface="org.freedesktop.Notifications",
        in_signature="",
        out_signature="ssss")
    def GetServerInformation(self):
        """
        @returns: a tuple containing the server name, the vendor name, the
                  server version and the supported protocol version.
        """
        return ("Notifications", "freedesktop.org", "0.1", "0.7.1")

    # Signals

    @dbus.service.signal(
        dbus_interface="org.freedesktop.Notifications",
        signature="uu")
    def NotificationClosed(self, id, reason):
        """
        reason is one of:
        1 - The notification expired.
        2 - The notification was dismissed by the user.
        3 - The notification was closed by a call to CloseNotification.
        4 - Undefined/reserved reasons.

        @param id: unsigned int
        @param reason: unsigned int
        """
        logging.debug("Successfully closed notification {}. Reason: {}"
            .format(id, reason))

    @dbus.service.signal(
        dbus_interface="org.freedesktop.Notifications",
        signature="us")
    def ActionInvoked(self, id, action_key):
        """
        @param id: unsigned int
        @param action_key: string
        """
        pass


def create_argument_parser():
    parser = argparse.ArgumentParser(
        description="A notification server implementing the specification from"
                    " http://developer.gnome.org/notification-spec/.")

    parser.add_argument(
        "-l", "--loglevel",
        dest="loglevel",
        default="WARNING",
        type=lambda value: value.upper(),
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="set the logging level")

    parser.add_argument(
        "-t", "--expire-timeout",
        dest="expireTimeout",
        default=10000,
        type=int,
        help="set the maximum/default timeout for notifications in [ms]")

    parser.add_argument(
        "-m", "--margins",
        dest="margins",
        default="0,0,0,0",
        type=lambda value: [int(x) for x in value.split(",")],
        help="set screen margins for top, right, bottom and left side of the"
               " screen in pixels")

    parser.add_argument(
        "-a", "--layout-anchor",
        dest="layoutAnchor",
        default="NORTH_EAST",
        type=lambda value: value.upper(),
        choices=["NORTH_WEST", "SOUTH_WEST", "SOUTH_EAST", "NORTH_EAST"],
        help="set the origin for the notifications")

    parser.add_argument(
        "-d", "--layout-direction",
        dest="layoutDirection",
        default="VERTICAL",
        type=lambda value: value.upper(),
        choices=["VERTICAL", "HORIZONTAL"],
        help="set the direction for the notifications")

    return parser


def main():
    parser = create_argument_parser()
    parser.formatter_class = argparse.ArgumentDefaultsHelpFormatter
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.loglevel))

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    loop = GLib.MainLoop()

    notDaemon = NotificationDaemon("/org/freedesktop/Notifications")
    notDaemon.max_expire_timeout = args.expireTimeout
    notDaemon.margins = args.margins
    notDaemon.layoutAnchor = getattr(LayoutAnchor, args.layoutAnchor)
    notDaemon.layoutDirection = getattr(LayoutDirection, args.layoutDirection)

    try:
        loop.run()
    except KeyboardInterrupt:
        logging.info("Exiting.")


if __name__ == '__main__':
    main()
