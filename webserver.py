'''
Copyright (c) 2018 Modul 9/HiFiBerry

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

from bottle import Bottle, template, static_file, response
from bottle.ext.websocket import GeventWebSocketServer, websocket

from metadata import Metadata, MetadataDisplay, MetadataEnrichLastFM


class AudioControlWebserver(MetadataDisplay):

    def __init__(self,
                 port=80,
                 host='0.0.0.0',
                 debug=False,
                 useLastFM=True):
        self.port = port
        self.host = host
        self.debug = debug
        self.useLastFM = useLastFM
        self.bottle = Bottle()
        self.route()
        self.controller = None
        thread = threading.Thread(target=self.startServer, args=())
        thread.daemon = True
        thread.start()
        logging.info("Started web server on port {}".format(self.port))

        # TODO: debug code
        self.websockets = set()
        self.notify(Metadata("Artist", "Title", "Album"))

        # Last.FM API to access additional track data

    def route(self):
        self.bottle.route('/',
                          method="GET",
                          callback=self.index_handler)
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
        return template('tpl/index.html', vars(self.metadata))

    def status_handler(self):
        response.content_type = 'text/plain; charset=UTF8'
        if self.controller is not None:
            return "Status\n\n{}".format(self.controller)
        else:
            return "Not connectedt to a controller"

    def websocket_handler(self, ws):
        print(ws)
        self.websockets.add(ws)
        print("Connected new web socket, now {} clients".format(
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
                logging.error("Can't parse command %s", msg)
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
                    "No controller connected, ignoring websocket command")

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

        if self.useLastFM:
            MetadataEnrichLastFM.enrich(metadata)

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

        md_json = json.dumps(vars(metadata))
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

    def __str__(self):
        return "webserver@{}".format(self.port)
