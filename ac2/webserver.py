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
import os
import copy
import urllib.parse

from bottle import Bottle, template, static_file, request, response
from bottle.ext.websocket import GeventWebSocketServer, websocket

from ac2.metadata import Metadata, MetadataDisplay, enrich_metadata

import hifiberryos.network as network


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

        # TODO: debug code
        self.websockets = set()
        self.notify(Metadata("Artist", "Title", "Album"))

        # Last.FM API to access additional track data

    def route(self):
        self.bottle.route('/',
                          method="GET",
                          callback=self.index_handler)
        self.bottle.route('/radio',
                          method="GET",
                          callback=self.radio_handler)
        self.bottle.route('/network',
                          method="GET",
                          callback=self.networkconfig_handler)
        self.bottle.route('/wifiscan',
                          method="GET",
                          callback=self.wifiscan_handler)
        self.bottle.route('/configurenetwork',
                          method="POST",
                          callback=self.configurenetwork_handler)
        self.bottle.route('/websocket',
                          method="GET",
                          callback=self.websocket_handler,
                          apply=websocket)
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
                        debug=self.debug,
                        server=GeventWebSocketServer)

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

    def index_handler(self):
        data = vars(self.metadata)
        # Check if LastFM is configured for a specific user and
        # enable/disable favorite feature
        if (self.lastfm_network is not None) and (
                self.lastfm_network.username is not None):
            data["support_favorites"] = 1
        else:
            data["support_favorites"] = 0

        data["volume"] = self.volume

        return template('tpl/index.html', data)

    def networkconfig_handler(self):
        data = network.get_current_config()
        data["systemname"] = "hifiberry"

        print(data)
        return template('tpl/network.html', data)

    def wifiscan_handler(self):
        data = network.find_networks()
        # TODO: sort by strength
        return data

    def configurenetwork_handler(self):
        data = network.find_networks()
        # TODO: sort by strength
        return data

    def radio_handler(self):
        url = request.query.stationurl
        if url is None or url == "":
            return template('tpl/radio.html',
                            {"stations": self.radio_stations})
        else:
            # Open URL using mpc
            logging.info("opening radio URL %s using mpc", url)
            commands = ["clear", "add {}", "play"]
            for cmd in commands:
                mycmd = "mpc {}".format(cmd.format(url))
                err = os.system(mycmd)
                if err:
                    logging.error("command %s failed with error %s",
                                  mycmd, err)

    def status_handler(self):
        response.content_type = 'text/plain; charset=UTF8'
        if self.player_control is not None:
            return "status\n\n{}".format(self.player_control)
        else:
            return "not connected to a player control"

    def websocket_handler(self, ws):
        print(ws)
        self.websockets.add(ws)
        print("connected new web socket, now {} clients".format(
            len(self.websockets)))
        while True:
            msg = ws.receive()
            if msg is None:
                self.websockets.remove(ws)
                logging.error("web socket closed")
                break

            parsed = json.loads(msg)
            try:
                command = parsed["command"].lower()
                if "params" in parsed:
                    params = parsed["params"]
                else:
                    params = None
                self.send_command(command, params)
            except:
                logging.error("can't parse command %s", msg)
                continue

    def static_handler(self, filename):
        return static_file(filename, root='static')

    def artwork_handler(self, filename):
        return static_file(self.artworkfile, root='/')

    # ##
    # ## end URL handlers
    # ##

    # ##
    # ## controller functions
    # ##

    def set_volume_control(self, volumecontrol):
        self.volume_control = volumecontrol

    def set_player_control(self, playercontrol):
        self.player_control = playercontrol

    def start(self):
        thread = threading.Thread(target=self.startServer, args=())
        thread.daemon = True
        thread.start()
        logging.info("started web server on port {}".format(self.port))

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

    # ##
    # ##  metadata functions
    # ##

    def notify(self, metadata):
        # Create a copy, because we might modify the artUrl
        metadata = copy.copy(metadata)
        self.metadata = metadata
        localfile = None

        enrich_metadata(metadata)

        if metadata.artUrl is None:
            metadata.artUrl = "static/unknown.png"

        elif metadata.artUrl.startswith("file://"):
            localfile = metadata.artUrl[7:]
        else:
            url = urllib.parse.urlparse(metadata.artUrl, scheme="file")
            if url.scheme == "file":
                localfile = url.path

        if localfile is not None:
            if os.path.isfile(localfile):
                self.artworkfile = localfile
                # use only file part of path name
                metadata.artUrl = "artwork/" + \
                    os.path.split(localfile)[1]
            else:
                metadata.artUrl = "static/unknown.png"

        self.send_websocket_update(vars(metadata))

    # ##
    # ##  metadata functions
    # ##

    def update_volume(self, vol):
        self.volume = vol
        self.send_websocket_update({"volume": vol})

    def send_websocket_update(self, dictionary):
        md_json = json.dumps(dictionary)

        # It's necessary to create a copy as the set might be modified here

        for ws in self.websockets.copy():

            try:
                ws.send(md_json)
            except Exception as e:
                # Web socket might be dead
                try:
                    print("remove ws" + e)
                    self.websockets.remove(ws)
                except:
                    pass

    def set_lastfm_network(self, lastfm_network):
        self.lastfm_network = lastfm_network

    def set_radio_stations(self, stations):
        self.radio_stations = stations

    def __str__(self):
        return "webserver@{}".format(self.port)
