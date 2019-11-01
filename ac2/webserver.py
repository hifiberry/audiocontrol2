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
from bottle import Bottle, static_file, request, response

from ac2.metadata import Metadata, MetadataDisplay


class AudioControlWebserver(MetadataDisplay):

    def __init__(self,
                 port=80,
                 host='0.0.0.0',
                 debug=False):
        self.port = port
        self.host = host
        self.debug = debug
        self.bottle = Bottle()
        self.route()
        self.player_control = None
        self.lastfm_network = None
        self.radio_stations = None
        self.volume_control = None
        self.volume = 0
        self.thread = None

        self.notify(Metadata("Artist", "Title", "Album"))

        # Last.FM API to access additional track data

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

    def startServer(self):
        self.bottle.run(port=self.port,
                        host=self.host,
                        debug=self.debug)

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

    def playerstatus_handler(self):

        if self.player_control is None:
            response.status = 501
            return "no player control available"

        states = self.player_control.states()

        return (states)

    def metadata_handler(self):
        print(self.metadata)
        return json.dumps(self.metadata.__dict__, skipkeys=True)

    def track_handler(self, command):
        if (command in "love", "unlove"):
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
        return static_file(self.artworkfile, root='/')

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

    # ##
    # ## metadata functions
    # ##
    def notify(self, metadata):
        self.metadata = metadata

    def update_volume(self, vol):
        self.volume = vol

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

        if command in ("next", "previous", "play", "pause", "playpause"):
            if self.player_control is None:
                logging.info(
                    "no controller connected, ignoring websocket command")

            try:
                if command == "next":
                    self.player_control.next()
                elif command == "previous":
                    self.player_control.previous()
                elif command == "play":
                    self.player_control.playpause(pause=False)
                elif command == "pause":
                    self.player_control.playpause(pause=True)
                elif command == "playpause":
                    self.player_control.playpause(pause=None)
                else:
                    logging.error("unknown command %s", command)
                    return False
            except:
                logging.error("failed to send command %s",
                              command)
                return False

            return True

    def love_track(self, love):
        try:
            track = self.lastfm_network.get_track(self.metadata.artist,
                                                  self.metadata.title)
            if love:
                logging.info("sending love to Last.FM")
                track.love()
            else:
                logging.info("sending unlove to Last.FM")
                track.love()
        except Exception as e:
            logging.warning("got exception %s while love/unlove", e)
            return False

        return True

    # ##
    # ## end controller functions
    # ##

    def __str__(self):
        return "webserver@{}".format(self.port)
