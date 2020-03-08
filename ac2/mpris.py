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
import copy
from random import randint
import threading

from ac2.metadata import Metadata, enrich_metadata_bg
# from ac2.controller import PlayerController
from ac2 import watchdog
from ac2.helpers import array_to_string
from usagecollector.client import report_usage

PLAYING = "playing"
PAUSED = "pauses"

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

SPOTIFY_NAME = "spotifyd"
LMS_NAME = "lms"


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
        self.supported_commands = []

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
        self.active_player = None
        self.ignore_players = ignore_players
        self.metadata = {}
        self.playing = False
        self.connect_dbus()
        self.metadata = Metadata()
        self.metadata_lock = threading.Lock()
        self.volume_control = None

    def register_metadata_display(self, mddisplay):
        self.metadata_displays.append(mddisplay)

    def set_volume_control(self, volume_control):
        self.volume_control = volume_control

    def metadata_notify(self, metadata):
        if metadata.is_unknown() and metadata.playerState == "playing":
            logging.error("Got empty metadata - what's wrong here? %s",
                          metadata)

        for md in self.metadata_displays:
            try:
                logging.debug("metadata_notify: %s %s", md, metadata)
                md.notify_async(copy.copy(metadata))
            except Exception as e:
                logging.warn("could not notify %s: %s", md, e)
                logging.exception(e)

        self.metadata = metadata

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

    def retrieveCommands(self, name):
        commands = {
            "pause": "CanPause",
            "next": "CanGoNext",
            "previous": "CanGoPrevious",
            "play": "CanPlay",
            "seek": "CanSeek"
        }
        try:
            supported_commands = ["stop"]  # Stop must always be supported
            device_prop = self.dbus_get_device_prop_interface(name)
            for command in commands:
                supported = device_prop.Get("org.mpris.MediaPlayer2.Player",
                                            commands[command])
                if supported:
                    supported_commands.append(command)
        except Exception as e:
            logging.warn("got exception %s", e)

        return supported_commands

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

            try:
                md.streamUrl = prop.get("xesam:url")
            except:
                pass

            try:
                md.trackId = prop.get("mpris:trackid")
            except:
                pass

            md.playerName = self.playername(name)

            md.fix_problems()

            return md

        except dbus.exceptions.DBusException as e:
            if "ServiceUnknown" in e.__class__.__name__:
                # unfortunately we can't do anything about this and
                # logging doesn't help, therefore just ignoring this case
                pass
                #  logging.warning("service %s disappered, cleaning up", e)
            else:
                logging.warning("no mpris data received %s", e.__class__.__name__)

            md = Metadata()
            md.playerName = self.playername(name)
            return md

    def mpris_command(self, playername, command):
        try:
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
        except Exception as e:
            logging.error("exception %s while sending MPRIS command %s to %s",
                          e, command, playername)
            return False

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
        if mprisname is None:
            return
        if (mprisname.startswith(MPRIS_PREFIX)):
            return mprisname[len(MPRIS_PREFIX):]
        else:
            return mprisname

    def send_command(self, command, playerName=None):
        res = None
        if playerName is None:
            if self.active_player is None:
                logging.info("No active player, ignoring %s", command)
                return
            else:
                playerName = self.active_player

        if playerName.startswith(MPRIS_PREFIX):
            res = self.mpris_command(playerName, command)
        else:
            res = self.mpris_command(MPRIS_PREFIX + playerName, command)
            
        logging.info("sent %s to %s", command, playerName)

        return res

    def activate_player(self, playername):

        command = MPRIS_PLAY
        if playername.startswith(MPRIS_PREFIX):
            res = self.mpris_command(playername, command)
        else:
            res = self.mpris_command(MPRIS_PREFIX + playername, command)

        return res

    def update_metadata_attributes(self, updates, songId):
        logging.debug("received metadata update: %s", updates)

        if self.metadata is None:
            logging.warn("ooops, got an update, but don't have metadata")
            return

        if self.metadata.songId() != songId:
            logging.debug("received update for previous song, ignoring")
            return

        # TODO: Check if this is the same song!
        # Otherwise it might be a delayed update

        with self.metadata_lock:
            for attribute in updates:
                self.metadata.__dict__[attribute] = updates[attribute]

        self.metadata_notify(self.metadata)

    def main_loop(self):
        """
        Main loop:
        - monitors state of all players
        - pauses players if a new player starts playback
        """

        finished = False
        md = Metadata()
        active_players = []

        MAX_FAIL = 3

        # Workaround for spotifyd problems
        spotify_stopped = 0

        # Workaround for squeezelite mute
        squeezelite_active = 0

        previous_state = ""
        ts = datetime.datetime.now()

        while not(finished):
            new_player_started = None
            metadata_notified = False
            playing = False
            new_song = False
            state = "unknown"
            last_ts = ts
            ts = datetime.datetime.now()
            duration = (ts-last_ts).total_seconds()

            for p in self.retrievePlayers():

                if self.playername(p) in self.ignore_players:
                    continue

                if p not in self.state_table:
                    ps = PlayerState()
                    ps.supported_commands = self.retrieveCommands(p)
                    logging.debug("Player %s supports %s",
                                  p,
                                  ps.supported_commands)
                    self.state_table[p] = ps

                thisplayer_state = "unknown"
                try:
                    thisplayer_state = self.retrieveState(p).lower()
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

                self.state_table[p].state = thisplayer_state

                # Check if playback started on a player that wasn't
                # playing before
                if thisplayer_state == PLAYING:
                    playing = True
                    state = "playing"

                    if self.playername(p) == SPOTIFY_NAME:
                        spotify_stopped = 0

                    if self.playername(p) == LMS_NAME:
                        squeezelite_active = 2
                        
                    report_usage("audiocontrol_playing_{}".format(self.playername(p)),duration)

                    md = self.retrieveMeta(p)


                    if (p not in active_players):
                        new_player_started = p
                        active_players.insert(0, p)

                    md.playerState = thisplayer_state

                    # MPRIS delivers only very few metadata, these will be
                    # enriched with external sources
                    if (md.sameSong(self.metadata)):
                        md.fill_undefined(self.metadata)
                    else:
                        new_song = True

                    self.state_table[p].metadata = md
                    if not(md.sameSong(self.metadata)):
                        logging.debug("updated metadata: \nold %s\nnew %s",
                                      self.metadata,
                                      md)
                        # Store this as "current"
                        with self.metadata_lock:
                            self.metadata = md

                        self.metadata_notify(md)
                        logging.debug("notifications about new metadata sent")
                    elif state != previous_state:
                        logging.debug("changed state to playing")
                        self.metadata_notify(md)

                    # Add metadata if this is a new song
                    if new_song:
                        enrich_metadata_bg(md, callback=self)
                        logging.debug("metadata updater thread started")

                    # Even if we din't send metadata, this is still
                    # flagged
                    metadata_notified = True
                else:

                    # always keep one player in the active_players
                    # list
                    if len(active_players) > 1:
                        if p in active_players:
                            active_players.remove(p)

                    # update metadata for stopped players from time to time
                    i = randint(0, 600)
                    if (i == 0):
                        md = self.retrieveMeta(p)
                        md.playerState = thisplayer_state
                        self.state_table[p].metadata = md

            self.playing = playing

            # Find active (or last paused) player
            if len(active_players) > 0:
                self.active_player = active_players[0]
            else:
                self.active_player = None

            # Workaround for wrong state messages by Spotify
            # Assume Spotify is still playing for 10 seconds if it's the
            # active (or last stopped) player
            if self.playername(self.active_player) == SPOTIFY_NAME and \
                not(playing):
                spotify_stopped += 1
                if spotify_stopped < 26:
                    if (spotify_stopped % 5) == 0:
                        logging.debug("spotify workaround %s", spotify_stopped)
                    playing = True

            # Woraround for LMS muting the output after stopping the
            # player
            if self.volume_control is not None:
                if self.playername(self.active_player) != LMS_NAME:
                    if squeezelite_active > 0:
                        squeezelite_active = squeezelite_active - 1
                        logging.debug("squeezelite was active before, unmuting")
                        self.volume_control.set_mute(False)

                if not(playing) and squeezelite_active > 0:
                    squeezelite_active = squeezelite_active - 1
                    logging.debug("squeezelite was active before, unmuting")
                    self.volume_control.set_mute(False)

            # There might be no active player, but one that is paused
            # or stopped
            if not(playing) and len(active_players) > 0:
                p = active_players[0]
                md = self.retrieveMeta(p)
                md.playerState = self.state_table[p].state
                state = md.playerState

            if state != previous_state:
                logging.debug("state transition %s -> %s",
                              previous_state, state)
                if not metadata_notified:
                    self.metadata_notify(md)

            previous_state = state

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

    # ##
    # ## controller functions
    # ##

    def previous(self):
        self.send_command(MPRIS_PREV)

    def next(self):
        self.send_command(MPRIS_NEXT)

    def playpause(self, pause=None):
        command = None
        if pause is None:
            if self.playing:
                command=MPRIS_PAUSE
            else:
                command=MPRIS_PLAY
        elif pause:
            command=MPRIS_PAUSE
        else:
            command=MPRIS_PLAY
                
        self.send_command(command)

    def stop(self):
            self.send_command(MPRIS_STOP)

    # ##
    # ## end controller functions
    # ##

    def __str__(self):
        return "mpris"

    def states(self):
        players = []
        for p in self.state_table:
            player = {}
            player["name"] = self.playername(p)
            player["state"] = self.state_table[p].state
            player["artist"] = self.state_table[p].metadata.artist
            player["title"] = self.state_table[p].metadata.title
            player["supported_commands"] = self.state_table[p].supported_commands;

            players.append(player)

        return {"players":players, "last_updated": str(self.last_update)}

