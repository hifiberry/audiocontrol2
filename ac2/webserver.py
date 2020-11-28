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

import logging
import threading
import json
import copy
import urllib.parse
import pathlib
import os

from bottle import Bottle, static_file, request, response
from expiringdict import ExpiringDict


from ac2.metadata import Metadata
from ac2.plugins.metadata import MetadataDisplay


class SystemControl():
    def __init__(self):
        pass

    def poweroff(self):
        return os.system('systemctl poweroff') == 0

class AudioControlWebserver(MetadataDisplay):

    def __init__(self,
                 port=80,
                 host='0.0.0.0',
                 authtoken=None,
                 debug=False):
        super().__init__()
        self.port = port
        self.host = host
        self.debug = debug
        self.authtoken = authtoken
        self.bottle = Bottle()
        self.route()
        self.system_control = SystemControl()
        self.player_control = None
        self.lastfm_network = None
        self.volume_control = None
        self.volume = 0
        self.thread = None
        self.lovers = []
        self.updaters = []
        self.artwork = ExpiringDict(max_len=100, max_age_seconds=36000000)

        self.notify(Metadata("Artist", "Title", "Album"))

        # Last.FM API to access additional track data

    def validate_authtoken(self, request):
        if self.authtoken is None:
            return False

        if "Authtoken" in request.headers and request.headers["Authtoken"] == self.authtoken:
            return True
        return False

    def route(self):
        self.bottle.route('/static/<filename>',
                          method="GET",
                          callback=self.static_handler)
        self.bottle.route('/artwork/<filename>',
                          method="GET",
                          callback=self.artwork_handler)
        self.bottle.route('/api/player/status',
                          method="GET",
                          callback=self.playerstatus_handler)
        self.bottle.route('/api/player/playing',
                          method="GET",
                          callback=self.playerplaying_handler)
        self.bottle.route('/api/player/activate/<player>',
                          method="POST",
                          callback=self.playeractivate_handler)
        self.bottle.route('/api/player/<command>',
                          method="POST",
                          callback=self.playercontrol_handler)
        self.bottle.route('/api/track/metadata',
                          method="GET",
                          callback=self.metadata_handler)
        self.bottle.route('/api/track/<command>',
                          method="POST",
                          callback=self.track_handler)
        self.bottle.route('/api/volume',
                          method="GET",
                          callback=self.volume_get_handler)
        self.bottle.route('/api/volume',
                          method="POST",
                          callback=self.volume_post_handler)
        self.bottle.route('/api/system/<command>',
                          method="POST",
                          callback=self.system_handler)

    def startServer(self):
        self.bottle.run(port=self.port,
                        host=self.host,
                        debug=self.debug)

    # A "lover" is an object that can "love" or "unlove" a song.
    def add_lover(self, lover):
        self.lovers.append(lover)

    # An "updaters" is an object that will be informed about metadata changes,
    # e.g. love/unlove or skipped song.
    def add_updater(self, updater):
        self.updaters.append(updater)

    # ##
    # ## begin URL handlers
    # ##

    def playercontrol_handler(self, command):
        try:
            if not(self.send_command(command)):
                response.status = 500
                return "{} failed".format(command)

        except Exception as e:
            response.status = 500
            return "{} failed with exception {}".format(command, e)

        return "ok"

    def playeractivate_handler(self, player):
        try:
            if not(self.activate_player(player)):
                response.status = 500
                return "activation of {} failed".format(player)

        except Exception as e:
            response.status = 500
            return "activate/{} failed with exception {}".format(player, e)

        return "ok"

    def playerstatus_handler(self):

        if self.player_control is None:
            response.status = 501
            return "no player control available"

        states = self.player_control.states()

        return (states)

    def playerplaying_handler(self):

        if self.player_control is None:
            response.status = 501
            return "no player control available"

        playing = False
        for state in self.player_control.states()["players"]:
            logging.error("State %s", state)
            if state["state"].lower() == "playing":
                playing = True
                break

        return ({"playing": playing})

    def system_handler(self, command):
        if not self.validate_authtoken(request):
            response.status = 403
            return "Not authorized"

        if command == "poweroff" and not self.system_control.poweroff():
            response.status = 500
            return "Could not poweroff"
        else:
            response.status = 501
            return "Unknown command {}".format(command)

    def metadata_handler(self):
        print(self.metadata)
        return json.dumps(self.metadata.__dict__, skipkeys=True)

    def track_handler(self, command):
        if (command in ["love", "unlove"]):
            if not(self.send_command(command)):
                response.status = 500
                return "{} failed".format(command)
        else:
            response.status = 501
            return "command %s not implemented".format(command)

    def volume_get_handler(self):

        if self.volume_control is None:
            response.status = 501
            return "no volume control available"

        return ({"percent":self.volume_control.current_volume()})

    def volume_post_handler(self):

        if self.volume_control is None:
            response.status = 501
            return "no volume control available"

        data = request.json
        if "percent" in data:
            vol = data["percent"]
            value = 0
            try:
                value = int(vol)
            except ValueError:
                response.status = 401
                return "invalid value {}".format(vol)

            if vol[0] in ['+', '-']:
                self.volume_control.change_volume_percent(value)
            else:
                self.volume_control.set_volume(value)
        else:
            response.status = 401
            return "percent value missing"

        return ({"percent":self.volume_control.current_volume()})

    def status_handler(self):
        response.content_type = 'text/plain; charset=UTF8'
        if self.player_control is not None:
            return "status\n\n{}".format(self.player_control)
        else:
            return "not connected to a player control"

    def static_handler(self, filename):
        return static_file(filename, root='static')

    def artwork_handler(self, filename):
        logging.info("artwork filename=%s",filename)
        realfile = self.artwork.get(filename)
        if realfile is None:
            logging.warning("%s does not exist in cache",filename)
            
        if not(pathlib.Path(realfile).exists()):
            logging.warning("%s does not exist",realfile)
            
        return static_file(realfile, root='/')

    # ##
    # ## end URL handlers
    # ##

    # ##
    # ##  thread methods
    # ##

    def start(self):
        self.thread = threading.Thread(target=self.startServer, args=())
        self.thread.daemon = True
        self.thread.start()
        logging.info("started web server on port {}".format(self.port))

    def is_alive(self):
        if self.thread is None:
            return True
        else:
            return self.thread.is_alive()

    # ##
    # ## end thread methods
    # ##
    
    ###
    ### Rewrite artwork URLs if necessary
    ###
    def process_metadata(self, metadata):
        
        if metadata.artUrl is None:
            return
        
        
        localfile=None
        if metadata.artUrl.startswith("file://"):
            localfile = metadata.artUrl[7:]
        else:
            url = urllib.parse.urlparse(metadata.artUrl, scheme="file")
            if url.scheme == "file":
                localfile = url.path
                
        if localfile is not None:
            if pathlib.Path(localfile).exists():
                # use only file part of path name, but keep it 
                key = str(localfile).replace("/","-").replace(" ","-")
                metadata.artUrl = "artwork/" + key
                self.artwork[key]=localfile
            else:
                logging.warn("artwork file %s does not exist, removing artUrl (%s)",
                             localfile,
                             metadata.artUrl)
                metadata.artUrl=None
                
            
    # ##
    # ## metadata functions
    # ##
    def notify(self, metadata):
        # Create a copy, because we might need to modify the artUrl
        metadata = copy.copy(metadata)
        self.metadata = metadata
               

    def update_volume(self, vol):
        self.volume = vol

    def send_metadata_update(self, updates, song_id = None):
        if song_id is None and self.metadata is not None:
            song_id = self.metadata.songId()
        for u in self.updaters:
            try:
                logging.debug("sending update %s to %s", u, updates)
                u.update_metadata_attributes(updates, song_id)
            except Exception as e:
                logging.warn("couldn't send update to %s: %s", u, e)

    # ##
    # ## end metadata functions
    # ##

    # ##
    # ## controller functions
    # ##

    def set_volume_control(self, volumecontrol):
        self.volume_control = volumecontrol

    def set_player_control(self, playercontrol):
        self.player_control = playercontrol

    def activate_player(self, playername):

        if self.player_control is None:
            logging.info(
                    "no controller connected, can't activate a player")
            return False

        logging.info("trying to activate %s", playername)
        return self.player_control.activate_player(playername)

    def send_command(self, command, params=None):
        if command == "love":
            return self.love_track(True)

        if command == "unlove":
            return self.love_track(False)

        if command == "volume":

            if self.volume_control is not None:
                try:
                    volume = int(params)
                    self.volume_control.set_volume(volume)
                except ValueError:
                    logging.error("%s is not a valid volume", params)
                    return False
            else:
                logging.debug(
                    "volume change requested, "
                    "but no volume controller available")

            return True

        if command in ("next", "previous", "play", "pause", "playpause", "stop"):
            if self.player_control is None:
                logging.info(
                    "no controller connected, ignoring websocket command")
                return False

            try:
                if command == "next":
                    self.player_control.next()
                    self.send_metadata_update({"skipped": True})
                elif command == "previous":
                    self.player_control.previous()
                elif command == "play":
                    self.player_control.playpause(pause=False)
                elif command == "pause":
                    self.player_control.playpause(pause=True)
                elif command == "playpause":
                    self.player_control.playpause(pause=None)
                elif command == "stop":
                    self.player_control.stop()
                else:
                    logging.error("unknown command %s", command)
                    return False
            except Exception as e:
                logging.error("failed to send command %s (%s)",
                              command, e)
                logging.exception(e)
                return False

            return True

    def love_track(self, love):
        ok = True

        for lover in self.lovers:
            try:
                lover.love(love)
            except Exception as e:
                ok = False
                logging.warn("Could not love/unlove via %s: %s", lover, e)

        if ok:
            self.send_metadata_update({"loved": love})

        return ok

    # ##
    # ## end controller functions
    # ##

    def __str__(self):
        return "webserver@{}".format(self.port)
