'''
Copyright (c) 2020 Modul 9/HiFiBerry

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

import logging

from ac2.helpers import map_attributes
from ac2.players import PlayerControl
from ac2.constants import CMD_NEXT, CMD_PREV, CMD_PAUSE, CMD_PLAYPAUSE, CMD_STOP, CMD_PLAY, CMD_SEEK, \
    CMD_RANDOM, CMD_NORANDOM, CMD_REPEAT_ALL, CMD_REPEAT_NONE, \
    STATE_PAUSED, STATE_PLAYING, STATE_STOPPED, STATE_UNDEF
from ac2.metadata import Metadata

   
MPD_STATE_PLAY="play"
MPD_STATE_PAUSE="pause"
MPD_STATE_STOPPED="stop"

MPD_ATTRIBUTE_MAP={
    "artist": "artist",
    "title": "title",
    "albumartist": "albumArtist",
    "album": "albumTitle",
    "disc": "discNumber",
    "track": "tracknumber", 
    "duration": "duration",
    "time": "time",
    "file": "streamUrl" 
    }

STATE_MAP={
    MPD_STATE_PAUSE: STATE_PAUSED,
    MPD_STATE_PLAY: STATE_PLAYING,
    MPD_STATE_STOPPED: STATE_STOPPED
}

    
from mpd import MPDClient
 

class MPDControl(PlayerControl):
    
    def __init__(self, args={}):
        self.client=None
        self.playername="MPD"
        if "port" in args:
            self.port=args["port"]
        else:
            self.port=6600
            
        if "host" in args:
            self.host=args["host"]
        else:
            self.host="localhost"
            
        if " timeout" in args:
            self.timeout=args["timeout"]
        else:
            self.timeout=5
            
        self.connect()

        
    def start(self):
        # No threading implemented
        pass
    
    
    def connect(self):
        if self.client is not None:
            return self.client
        
        self.client = MPDClient()
        self.client.timeout = self.timeout
        try:
            self.client.connect(self.host, self.port)
            logging.info("Connected to %s:%s",self.host, self.port)
        except:
            self.client=None
        
        
    def disconnect(self):
        if self.client is None:
            return
        
        try:
            self.client.close()
            self.client.disconnect()
        except:
            pass
        
        self.client=None
        
    def get_supported_commands(self):
        return [CMD_NEXT, CMD_PREV, CMD_PAUSE, CMD_PLAYPAUSE, CMD_STOP, CMD_PLAY, CMD_SEEK,
                CMD_RANDOM, CMD_NORANDOM, CMD_REPEAT_ALL, CMD_REPEAT_NONE]   
            
    
    def get_state(self):
        if self.client is None:
            self.reconnect()

        if self.client is None:
            return {}
        
        try:
            status=self.client.status()
        except:
            # Connection to MPD might be broken
            self.disconnect()
            self.connect()
    
        
        try:
            state = STATE_MAP[status["state"]]
        except:
            state = STATE_UNDEF
            
        return state
    
        
    def get_meta(self):
        state=self.get_state()
        
        song = None
        if state in [STATE_PLAYING,STATE_PAUSED]:
            song=self.client.currentsong()
             
        md = Metadata()
        md.playerName = "mpd"
        
        if song is not None:
            map_attributes(song, md.__dict__,MPD_ATTRIBUTE_MAP)
        
        return md
    
    def send_command(self,command, parameters={}):
        if command not in self.get_supported_commands():
            return False 
        
        if self.client is None:
            self.reconnect()

        if self.client is None:
            return False
        
        playstate=None
        if command in [CMD_PLAY, CMD_PLAYPAUSE]:
            playstate=self.get_state()
        
        if command == CMD_NEXT:
            self.client.next()
        elif command == CMD_PREV:
            self.client.previous()
        elif command == CMD_PAUSE:
            self.client.pause(1)
        elif command == CMD_STOP:
            self.client.stop()
        elif command == CMD_RANDOM:
            self.client.random(1)
        elif command == CMD_NORANDOM:
            self.client.random(0)
        elif command == CMD_REPEAT_ALL:
            self.client.repeat(1)
        elif command == CMD_REPEAT_NONE:
            self.client.repeat(0)
        elif command == CMD_REPEAT_ALL:
            self.client.repeat(1)
        elif command == CMD_PLAY:
            if playstate == STATE_PAUSED:
                self.client.pause(0)
            else:
                self.client.play(0)
        elif command == CMD_PLAYPAUSE:
            if playstate == STATE_PLAYING:
                self.client.pause(1)
            else:
                self.send_command(CMD_PLAY)
        else:
            logging.warning("command %s not implemented", command)
            
        
    """
    Checks if a player is active on the system and can result a 
    state. This does NOT mean this player is running
    """
    def is_active(self):
        return self.client is not None
    