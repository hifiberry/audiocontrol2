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


import time
import logging
import datetime
import copy
from random import randint
import threading

from ac2.constants import CMD_NEXT, CMD_PAUSE, CMD_PLAY, CMD_PLAYPAUSE, \
    CMD_PREV, CMD_SEEK, CMD_STOP, STATE_PLAYING, STATE_PAUSED, STATE_STOPPED

from ac2.players.mpdcontrol import MPDControl
from ac2.players.mpris import MPRIS, MPRIS_PREFIX
from ac2.metadata import Metadata, enrich_metadata_bg
# from ac2.controller import PlayerController
from ac2 import watchdog

from usagecollector.client import report_usage

mpris = None

# SPOTIFY_NAME = "spotifyd"
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


class AudioController():
    """
    Controller for MPRIS and non-MPRIS media players
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
        self.metadata = Metadata()
        self.metadata_lock = threading.Lock()
        self.volume_control = None
        self.metadata_processors = []
        self.state_displays = []
        self.players={}
        self.mpris = MPRIS()
        self.mpris.connect_dbus()
        
    
    """
    Register a non-mpris player controls
    """
    def register_nonmpris_player(self,name,controller):
        self.players[name]=controller
        
    def register_metadata_display(self, mddisplay):
        self.metadata_displays.append(mddisplay)

    def register_state_display(self, statedisplay):
        self.state_displays.append(statedisplay)

    def register_metadata_processor(self, mdproc):
        self.metadata_processors.append(mdproc)

    def set_volume_control(self, volume_control):
        self.volume_control = volume_control

    def metadata_notify(self, metadata):
        if metadata.is_unknown() and metadata.playerState == "playing":
            logging.warning("Metadata without artist, album or title - what's wrong here? %s",
                          metadata)

        for md in self.metadata_displays:
            try:
                logging.debug("metadata_notify: %s %s", md, metadata)
                md.notify_async(copy.copy(metadata))
            except Exception as e:
                logging.warn("could not notify %s: %s", md, e)
                logging.exception(e)

        self.metadata = metadata


    def all_players(self):
        """
        Returns a list of MPRIS and non-MPRIS players
        """
        players=list(self.players.keys())+self.mpris.retrieve_players()
        logging.debug("players: %s",players)
        return players
        

    def get_player_state(self, name):
        """
        Returns the playback state for the given player instance
        
        It can handle both MPRIS and non-MPRIS players
        """
        
        if name in self.players.keys():
            return self.players[name].get_state()
        else:
            return self.mpris.retrieve_state(name)
        
    def get_supported_commands(self, name):
        if name in self.players.keys():
            return self.players[name].get_supported_commands()
        else:
            return self.mpris.get_supported_commands(name)
        
        
    def send_command_to_player(self,name,command):
        if name in self.players.keys():
            self.players[name].send_command(command)
        else:
            self.mpris.send_command(name,command)
            
    def pause_inactive(self, active_player):
        """
        Automatically pause other player if playback was started
        on a new player
        """
        for p in self.state_table:
            if (p != active_player) and \
                    (self.state_table[p].state == STATE_PLAYING):
                logging.info("Pausing " + self.playername(p))
                self.send_command(p, CMD_PAUSE)


    def pause_all(self):
        for player in self.state_table:
            self.send_command(player, CMD_PAUSE)

    def print_players(self):
        for p in self.state_table:
            print(self.playername(p))

    def playername(self, name):
        if name is None:
            return
        if (name.startswith(MPRIS_PREFIX)):
            return name[len(MPRIS_PREFIX):]
        else:
            return name

    def send_command(self, command, playerName=None):
        if playerName is None:
            if self.active_player is None:
                logging.info("No active player, ignoring %s", command)
                return
            else:
                playerName = self.active_player

        res = self.send_command_to_player(playerName, command)    
        logging.info("sent %s to %s", command, playerName)

        return res

    def activate_player(self, playername):

        command = CMD_PLAY
        if playername.startswith(MPRIS_PREFIX):
            res = self.send_command_to_player(playername, command)
        else:
            res = self.mpris_command(MPRIS_PREFIX + playername, command)

        return res
    
    
    def get_meta(self, name):
        if name in self.players.keys():
            md=self.players[name].get_meta()
        else:
            md=self.mpris.get_meta(name)
            
        if md is None:
            return None
        
        md.fix_problems()
            
        for p in self.metadata_processors:
            p.process_metadata(md)
            
        return md
                
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
#        spotify_stopped = 0

        # Workaround for squeezelite mute
        squeezelite_active = 0

        previous_state = ""
        ts = datetime.datetime.now()

        while not(finished):
            additional_delay = 0
            new_player_started = None
            metadata_notified = False
            playing = False
            new_song = False
            state = "unknown"
            last_ts = ts
            ts = datetime.datetime.now()
            duration = (ts-last_ts).total_seconds()

            for p in self.all_players():

                if self.playername(p) in self.ignore_players:
                    continue
                
                if p not in self.state_table:
                    ps = PlayerState()
                    ps.supported_commands = self.get_supported_commands(p)
                    logging.debug("Player %s supports %s",
                                  p,
                                  ps.supported_commands)
                    self.state_table[p] = ps

                thisplayer_state = "unknown"
                try:
                    thisplayer_state = self.get_player_state(p).lower()
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
                if thisplayer_state == STATE_PLAYING:
                    playing = True
                    state = "playing"

#                    if self.playername(p) == SPOTIFY_NAME:
#                        spotify_stopped = 0

                    if self.playername(p) == LMS_NAME:
                        squeezelite_active = 2
                        
                    report_usage("audiocontrol_playing_{}".format(self.playername(p)),duration)

                    md = self.get_meta(p)


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
                        
                    # Some players deliver artwork after initial metadata
                    if md.artUrl != self.metadata.artUrl:
                        logging.debug("artwork changes from %s to %s",
                                      self.metadata.artUrl,
                                      md.artUrl)
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
                        md = self.get_meta(p)
                        md.playerState = thisplayer_state
                        self.state_table[p].metadata = md

            self.playing = playing

            # Find active (or last paused) player
            if len(active_players) > 0:
                self.active_player = active_players[0]
            else:
                self.active_player = None

#             # Workaround for wrong state messages by Spotify
#             # Assume Spotify is still playing for 10 seconds if it's the
#             # active (or last stopped) player
#             if self.playername(self.active_player) == SPOTIFY_NAME:
#                 # Less aggressive metadata polling on Spotify as each polling will 
#                 # result in an API request
#                 additional_delay = 4
#                 if not(playing):
#                     spotify_stopped += 1 + additional_delay
#                     if spotify_stopped < 26:
#                         if (spotify_stopped % 5) == 0:
#                             logging.debug("spotify workaround %s", spotify_stopped)
#                         playing = True
#                     

            # Workaround for LMS muting the output after stopping the
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
                md = self.get_meta(p)
                md.playerState = self.state_table[p].state
                state = md.playerState

            if state != previous_state:
                logging.debug("state transition %s -> %s",
                              previous_state, state)
                if not metadata_notified:
                    self.metadata_notify(md)
                for sd in self.state_displays:
                    sd.update_playback_state(state)

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

            time.sleep(self.loop_delay+additional_delay)

    # ##
    # ## controller functions
    # ##

    def previous(self):
        self.send_command(CMD_PREV)

    def next(self):
        self.send_command(CMD_NEXT)

    def playpause(self, pause=None, ignore=None):
        
        if ignore is not None:
            if self.active_player.lower() == ignore.lower():
                logging.info("Got a playpquse request that should be ignored (%s)",
                             ignore)
                return
        
        command = None
        if pause is None:
            if self.playing:
                command=CMD_PAUSE
            else:
                command=CMD_PLAY
        elif pause:
            command=CMD_PAUSE
        else:
            command=CMD_PLAY
                
        self.send_command(command)

    def stop(self):
            self.send_command(CMD_STOP)

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

