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

from bottle import Bottle, template, static_file
from bottle.ext.websocket import GeventWebSocketServer, websocket

from metadata import Metadata, MetadataDisplay


class AudioControlWebserver( MetadataDisplay ):

    def __init__( self, port=8080 ):
        self.port = port
        self.bottle = Bottle()
        self.route()

        thread = threading.Thread( target=self.startServer, args=() )
        thread.daemon = True
        thread.start()
        logging.info( "Started web server on port {}".format( self.port ) )

        # TODO: debug code
        self.metadata = Metadata( "Artist", "Title", "Album" )
        self.websockets = set()

    def route( self ):
        self.bottle.route( '/',
                           method="GET",
                           callback=self.index_handler )
        self.bottle.route( '/websocket',
                           method="GET",
                           callback=self.websocket_handler,
                           apply=websocket )
        self.bottle.route( '/static/<filename>',
                           method="GET",
                           callback=self.static_handler )

    def startServer( self ):
        # TODO: Remove debug mode when finished
        self.bottle.run( port=self.port,
                         debug=True,
                         server=GeventWebSocketServer )

    # ##
    # ## begin URL handlers
    # ##
    def index_handler( self ):
        return template( 'tpl/index.html' )

    def websocket_handler( self, ws ):
        print( ws );
        self.websockets.add( ws )
        print( "Connected new web socket, now {} clients".format( 
                      len( self.websockets ) ) )
        while True:
            msg = ws.receive()
            if msg is None:
                self.websockets.remove( ws )
                break

    def static_handler( self, filename ):
        return static_file( filename, root='static' )

    # ##
    # ## end URL handlers
    # ##

    def notify( self, metadata ):
        self.metadata = metadata
        md_json = json.dumps( vars( metadata ) )
        # It's necessary to create a copy as the set might be modified here
        for ws in self.websockets.copy():
            # TO DO:
            # file:// artUrls to base64 data stream
            try:
                ws.send( md_json )
            except Exception as e:
                # Web socket might be dead
                try:
                    print( "remove ws" + e )
                    self.websockets.remove( ws )
                except:
                    pass

