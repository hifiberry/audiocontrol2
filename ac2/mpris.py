'''
Copyright (c) 2019 Modul 9/HiFiBerry

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import dbus
import time
import logging
import datetime

from ac2.metadata import Metadata
# from ac2.controller import PlayerController
from ac2 import watchdog
from ac2.helpers import array_to_string

PLAYING = "playing"
PAUSED = "playing"

mpris = None

MPRIS_NEXT = "Next"
MPRIS_PREV = "Previous"
MPRIS_PAUSE = "Pause"
MPRIS_PLAYPAUSE = "PlayPause"
MPRIS_STOP = "Stop"
MPRIS_PLAY = "Play"

MPRIS_PREFIX = "org.mpris.MediaPlayer2."

mpris_commands = [MPRIS_NEXT, MPRIS_PREV,
                  MPRIS_PAUSE, MPRIS_PLAYPAUSE,
                  MPRIS_STOP, MPRIS_PLAY]


class PlayerState:
    """
    Internal representation of the state of a player
    """

    def __init__(self, state="unknown", metadata=None, failed=0):
        self.state = state
        self.failed = failed
        if metadata is not None:
            self.metadata = metadata
        else:
            self.metadata = Metadata()

    def __str__(self):
        return self.state + str(self.metadata)


class MPRISController():
    """
    Controller for MPRIS enabled media players
    """

    def __init__(self, auto_pause=True, loop_delay=1, ignore_players=[]):
        self.state_table = {}
        self.auto_pause = auto_pause
        self.metadata_displays = []
        self.last_update = None
        self.loop_delay = loop_delay
        self.ignore_players = ignore_players
        self.connect_dbus()

    def register_metadata_display(self, mddisplay):
        self.metadata_displays.append(mddisplay)

    def metadata_notify(self, metadata):
        for md in self.metadata_displays:
            logging.debug("metadata_notify: %s %s", md, metadata)
            md.notify(metadata)

    def connect_dbus(self):
        self.bus = dbus.SystemBus()
        self.device_prop_interfaces = {}

    def dbus_get_device_prop_interface(self, name):
        proxy = self.bus.get_object(name, "/org/mpris/MediaPlayer2")
        device_prop = dbus.Interface(
            proxy, "org.freedesktop.DBus.Properties")
        return device_prop

    def retrievePlayers(self):
        """
        Returns a list of all MPRIS enabled players that are active in
        the system
        """
        return [name for name in self.bus.list_names()
                if name.startswith("org.mpris")]

    def retrieveState(self, name):
        """
        Returns the playback state for the given player instance
        """
        try:
            device_prop = self.dbus_get_device_prop_interface(name)
            state = device_prop.Get("org.mpris.MediaPlayer2.Player",
                                    "PlaybackStatus")
            return state
        except Exception as e:
            logging.warn("got exception %s", e)

    def retrieveMeta(self, name):
        """
        Return the metadata for the given player instance
        """
        try:
            device_prop = self.dbus_get_device_prop_interface(name)
            prop = device_prop.Get(
                "org.mpris.MediaPlayer2.Player", "Metadata")
            try:
                artist = array_to_string(prop.get("xesam:artist"))
            except:
                artist = None

            try:
                title = prop.get("xesam:title")
            except:
                title = None

            try:
                albumArtist = array_to_string(prop.get("xesam:albumArtist"))
            except:
                albumArtist = None

            try:
                albumTitle = prop.get("xesam:album")
            except:
                albumTitle = None

            try:
                artURL = prop.get("mpris:artUrl")
            except:
                artURL = None

            try:
                discNumber = prop.get("xesam:discNumber")
            except:
                discNumber = None

            try:
                trackNumber = prop.get("xesam:trackNumber")
            except:
                trackNumber = None

            md = Metadata(artist, title, albumArtist, albumTitle,
                          artURL, discNumber, trackNumber)

            md.playerName = self.playername(name)

            md.fixProblems()

            return md

        except dbus.exceptions.DBusException as e:
            logging.warning("no mpris data received %s", e)
            md = Metadata()
            md.playerName = self.playername(name)

            return md

    def mpris_command(self, playername, command):
        if command in mpris_commands:
            proxy = self.bus.get_object(playername,
                                        "/org/mpris/MediaPlayer2")
            player = dbus.Interface(
                proxy, dbus_interface='org.mpris.MediaPlayer2.Player')

            run_command = getattr(player, command,
                                  lambda: "Unknown command")
            return run_command()
        else:
            logging.error("MPRIS command %s not supported", command)

    def pause_inactive(self, active_player):
        """
        Automatically pause other player if playback was started
        on a new player
        """
        for p in self.state_table:
            if (p != active_player) and \
                    (self.state_table[p].state == PLAYING):
                logging.info("Pausing " + self.playername(p))
                self.mpris_command(p, MPRIS_PAUSE)

    def pause_all(self):
        for player in self.state_table:
            self.mpris_command(player, MPRIS_PAUSE)

    def print_players(self):
        for p in self.state_table:
            print(self.playername(p))

    def playername(self, mprisname):
        if (mprisname.startswith(MPRIS_PREFIX)):
            return mprisname[len(MPRIS_PREFIX):]
        else:
            return mprisname

    def send_command(self, command, playerName=None):
        if playerName is None:
            return
        elif playerName.startswith(MPRIS_PREFIX):
            self.mpris_command(playerName, command)
        else:
            self.mpris_command(MPRIS_PREFIX + playerName, command)

    def main_loop(self):
        """
        Main loop:
        - monitors state of all players
        - pauses players if a new player starts palyback
        """

        finished = False
        md = Metadata()
        active_players = []
        md_prev = None
        MAX_FAIL = 3

        while not(finished):
            new_player_started = None
            metadata_notified = False

            for p in self.retrievePlayers():

                if self.playername(p) in self.ignore_players:
                    continue

                if p not in self.state_table:
                    self.state_table[p] = PlayerState()

                try:
                    state = self.retrieveState(p).lower()
                    self.state_table[p].failed = 0
                except:
                    logging.info("Got no state from " + p)
                    state = "unknown"
                    self.state_table[p].failed = \
                        self.state_table[p].failed + 1
                    if self.state_table[p].failed >= MAX_FAIL:
                        playername = self.playername(p)
                        logging.warning(
                            "%s failed, trying to restart", playername)
                        watchdog.restart_service(playername)
                        self.state_table[p].failed = 0

                self.state_table[p].state = state

                # Check if playback started on a player that wasn't
                # playing before
                if state == PLAYING:
                    if (p not in active_players):
                        new_player_started = p
                        active_players.insert(0, p)

                    md = self.retrieveMeta(p)
                    md.playerState = state

                    self.state_table[p].metadata = md
                    if md != md_prev:
                        self.metadata_notify(md)

                    md_prev = md

                    # Even if we din't send metadata, this is still
                    # flagged
                    metadata_notified = True
                else:
                    # always keep one player in the active_players
                    # list
                    if len(active_players) > 1:
                        if p in active_players:
                            active_players.remove(p)

            # There might be no active player, but one that is paused
            # or stopped
            if not metadata_notified and len(active_players) > 0:
                p = active_players[0]
                logging.debug(
                    "no active player playing, selecting the first one: %s",
                    p)
                md = self.retrieveMeta(p)
                md.playerState = self.state_table[p].state
                if md != md_prev:
                    self.metadata_notify(md)
                    md_prev = md

                md_prev = md

            if new_player_started is not None:
                if self.auto_pause:
                    logging.info(
                        "new player %s started, pausing other active players",
                        self.playername(active_players[0]))
                    self.pause_inactive(new_player_started)
                else:
                    logging.debug("auto-pause disabled")

            self.last_update = datetime.datetime.now()

            time.sleep(self.loop_delay)

    def __str__(self):
        """
        String representation of the current state: all players,
        playback state and meta data
        """
        res = ""
        for p in self.state_table:
            res = res + "{:30s} - {:10s}: {}/{}\n".format(
                self.playername(p),
                self.state_table[p].state,
                self.state_table[p].metadata.artist,
                self.state_table[p].metadata.title)

        res = res + "\nLast updated {}\n".format(self.last_update)

        return res
