===
ktm
===


ktm (a.k.a. kill the messenger!) is a configurable notification daemon with queues and history display

    - Free software: GPL V3+ License
    - Documentation will be available at: http://ktm.readthedocs.org.


This project has been originally fork from https://github.com/the-isz/notipy

Many thanks to its author!

The following documentation is taken from the notipy project, and is meant to be changed
-----------------------------------------------------------------------------------------


ktm (aka kill the messenger!) is an implementation of the http://developer.gnome.org/notification-spec/[Desktop Notification Specification]. It shows
message popups using gtk3, allowing for pango marked up message bodies and icons
that can be specified in various ways.

.. image:: https://github.com/the-isz/notipy/raw/master/doc/screen.png


The design goals of notipy include a minimalistic implementation (following the
unix philosophy "do one thing and do it well") and having as little as possible
dependencies.

Installation
------------

ktm requires the following libraries to work:

 - gtk3
 - pygobject
 - dbus-python

Installation is simply done via::

    ./deployment/setup.py install

Configuration
-------------

Until now, ktm is configured exclusively via command-line arguments. These
can be listed via the --help command-line option::

    usage: ktm.py [-h] [-l {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [-t EXPIRETIMEOUT] [-m MARGINS]
                     [-a {NORTH_WEST,SOUTH_WEST,SOUTH_EAST,NORTH_EAST}] [-d {VERTICAL,HORIZONTAL}]

    A notification server implementing the specification from http://developer.gnome.org/notification-spec/.

    optional arguments:
      -h, --help            show this help message and exit
      -l {DEBUG,INFO,WARNING,ERROR,CRITICAL}, --loglevel {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                            set the logging level (default: WARNING)
      -t EXPIRETIMEOUT, --expire-timeout EXPIRETIMEOUT
                            set the maximum/default timeout for notifications in [ms] (default: 10000)
      -m MARGINS, --margins MARGINS
                            set screen margins for top, right, bottom and left side of the screen in pixels (default: 0,0,0,0)
      -a {NORTH_WEST,SOUTH_WEST,SOUTH_EAST,NORTH_EAST}, --layout-anchor {NORTH_WEST,SOUTH_WEST,SOUTH_EAST,NORTH_EAST}
                            set the origin for the notifications (default: NORTH_EAST)
      -d {VERTICAL,HORIZONTAL}, --layout-direction {VERTICAL,HORIZONTAL}
                            set the direction for the notifications (default: VERTICAL)




