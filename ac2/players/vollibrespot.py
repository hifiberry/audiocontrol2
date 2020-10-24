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

import socket
import logging
import threading
import json

from ac2.helpers import map_attributes
from ac2.players import PlayerControl
from ac2.constants import CMD_NEXT, CMD_PREV, CMD_PAUSE, CMD_PLAYPAUSE, CMD_PLAY, \
    STATE_PAUSED, STATE_PLAYING, STATE_UNDEF
from ac2.metadata import Metadata

VOLSPOTIFY_HELO = 0x1
VOLSPOTIFY_HEARTBEAT = 0x2
VOLSPOTIFY_TOKEN = 0x3
VOLSPOTIFY_PAUSE = 0x4
VOLSPOTIFY_PLAY = 0x5
VOLSPOTIFY_PLAYPAUSE = 0x6
VOLSPOTIFY_NEXT = 0x7
VOLSPOTIFY_PREV = 0x8
   
VOLSPOTIFY_ATTRIBUTE_MAP={
    "album_name": "albumTitle",
    "artist_name": "artist",
    "track_name": "title" 
}

VOLSPOTIFY_CMD_MAP={
    CMD_NEXT: VOLSPOTIFY_NEXT,
    CMD_PREV: VOLSPOTIFY_PREV,
    CMD_PAUSE: VOLSPOTIFY_PAUSE,
    CMD_PLAYPAUSE: VOLSPOTIFY_PLAYPAUSE,
    CMD_PLAY: VOLSPOTIFY_PLAY
}

    
class VollibspotifyControl(PlayerControl):
    
    def __init__(self, args={}):
        self.client=None
        self.playername="spotifyd"
        self.state = STATE_UNDEF
        self.metadata = Metadata()

        if "port" in args:
            self.port=args["port"]
        else:
            self.port=5030
            
        if "host" in args:
            self.host=args["host"]
        else:
            self.host="localhost"
            
    def start(self):
        self.listener = VollibspotifyMetadataListener(self)
        self.listener.start()
    
    def get_supported_commands(self):
        return [CMD_NEXT, CMD_PREV, CMD_PAUSE, CMD_PLAYPAUSE, CMD_PLAY]   
            
    def get_state(self):
        return self.state
        
    def get_meta(self):
        return self.metadata
    
    def send_command(self,command, parameters={}, mapping=True):
        if mapping and command not in self.get_supported_commands():
            return False
        
        if mapping:
            cmd = VOLSPOTIFY_CMD_MAP[command]
        else:
            cmd=command
             
        serverAddressPort = (self.host, self.port+1)
        UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        UDPClientSocket.sendto(bytes([cmd]), serverAddressPort)
        logging.debug("sent %s to vollibrespot",cmd)

    def is_active(self):
        return True
    
    
    
class VollibspotifyMetadataListener(threading.Thread):
    
    def __init__(self, control):
        threading.Thread.__init__(self)
        self.control = control
        self.finished=False
          
    def run(self):
        bufferSize  = 4096
        
        # Create a datagram socket
        serverSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        serverSocket.bind((self.control.host, self.control.port))

        while(not self.finished):
            bytesAddressPair = serverSocket.recvfrom(bufferSize)
            message = bytesAddressPair[0]
            try:
                message=message.decode("utf-8") 
            except:
                logging.warning("can't decode %s", message)
                message=""
                
                
            if message=="kSpPlaybackInactive":
                self.control.state = STATE_PAUSED
            elif message=="kSpSinkInactive":
                self.control.state = STATE_PAUSED
            elif message=="kSpSinkActive":
                self.control.state = STATE_PLAYING
            elif message[0]=='{':
                self.parse_message(message)
            elif message=="\r\n":
                pass
            else:
                logging.error("Don't know what to do with %s",message)
                
    def parse_message(self,message):
        try: 
            data = json.loads(message)
            if "metadata" in data:
                md = Metadata()
                map_attributes(data["metadata"], md.__dict__, VOLSPOTIFY_ATTRIBUTE_MAP)
            elif "position_ms" in data:
                pos=float(data["position_ms"])/1000
                self.control.metadata.position = pos
            else:
                logging.warn("don't know how to handle %s",data)
                
        except Exception as e:
            logging.error("error while parsing %s (%s)", message,e)
