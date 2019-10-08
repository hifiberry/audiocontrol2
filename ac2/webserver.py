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
        self.controller = None
        self.lastfm_network = None
        self.radio_stations = None
        self.volume_control = None
        self.volume = 0
        thread = threading.Thread(target=self.startServer, args=())
        thread.daemon = True
        thread.start()
        logging.info("started web server on port {}".format(self.port))

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
        self.bottle.route('/playerstatus',
                          method="GET",
                          callback=self.status_handler)

    def startServer(self):
        # TODO: Remove debug mode when finished
        self.bottle.run(port=self.port,
                        host=self.host,
                        debug=self.debug,
                        server=GeventWebSocketServer)

    # ##
    # ## begin URL handlers
    # ##
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
        if self.controller is not None:
            return "status\n\n{}".format(self.controller)
        else:
            return "not connectedt to a controller"

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
                command = parsed["command"]
                playerName = parsed["playerName"]
            except:
                logging.error("can't parse command %s", msg)
                continue

            if command == "love":
                self.love_track(True)
                continue

            if command == "unlove":
                self.love_track(False)
                continue

            if command == "volume":
                if "param" in parsed:
                    volume = parsed["param"]
                else:
                    logging.warning(
                        "volume change request without volume value")
                    continue

                if self.volume_control is not None:
                    self.volume_control.set_volume(volume)
                else:
                    logging.debug(
                        "volume change requested, but no volume controller available")
                continue

            if self.controller is not None:
                try:
                    self.controller.send_command(command=command,
                                                 playerName=playerName)
                except:
                    logging.error("Failed to send MPRIS command %s to %s",
                                  command, playerName)
            else:
                logging.info(
                    "no controller connected, ignoring websocket command")

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

    def static_handler(self, filename):
        return static_file(filename, root='static')

    def artwork_handler(self, filename):
        return static_file(self.artworkfile, root='/')

    # ##
    # ## end URL handlers
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

    def set_controller(self, controller):
        self.controller = controller

    def set_lastfm_network(self, lastfm_network):
        self.lastfm_network = lastfm_network

    def set_radio_stations(self, stations):
        self.radio_stations = stations

    def __str__(self):
        return "webserver@{}".format(self.port)
