import threading


class Metadata:
    """
    Class to start metadata of a song
    """

    def __init__(self, artist=None, title=None,
                 albumArtist=None, albumTitle=None, artUrl=None,
                 discNumber=None, trackNumber=None,
                 playerName=None, fixProblems=True):
        self.artist = artist
        self.title = title
        self.albumArtist = albumArtist
        self.albumTitle = albumTitle
        self.artUrl = artUrl
        self.discNumber = discNumber
        self.tracknumber = trackNumber
        self.playerName = playerName
        if fixProblems:
            self.fixProblems()

    def sameSong(self, other):
        if not isinstance(other, Metadata):
            return NotImplemented

        return self.artist == other.artist and self.title == other.title

    def fixProblems(self):
        """
        Cleanup metadata for known problems
        """

        # unknown artist, but artist - title in title
        # seen on mpd web radio streams
        if (self.playerName == "mpd") and \
            (self.artist == "unknown artist") and \
                (" - " in self.title):
            [artist, title] = self.title.split(" - ", 2)
            self.artist = artist
            self.title = title

    def __str__(self):
        return "{}: {} ({}) {}".format(self.artist, self.title,
                                       self.albumTitle, self.artUrl)


class MetadataDisplay:

    def __init__(self):
        pass

    def metadata(self, metadata):
        pass


class MetadataConsole(MetadataDisplay):

    def __init__(self):
        super()
        pass

    def metadata(self, metadata):
        print("{:16s}: {}".format(metadata.playerName, metadata))


import http.server


class MetadataHandler(http.server.BaseHTTPRequestHandler):

    @classmethod
    def set_metadata(cls, metadata):
        cls.metadata = metadata

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        print("GET")
        self._set_headers()
#        self.wfile.write("<html><body><h1>{}: {}</h1></body></html>".format(
#            MetadataHandler.metadata.artist,
#            MetadataHandler.self.metadata.title
#       ))
        self.wfile.write("<html><body><h1>Hi!</h1></body></html>")
        print("GET done")

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        # Doesn't do anything with posted data
        self._set_headers()
        self.wfile.write("<html><body><h1>POST!</h1></body></html>")


class MetadataWebserver(MetadataDisplay):

    def __init__(self, port=8080):
        self.port = port
        super()

    def run_server(self):
        import socketserver

        self.server = socketserver.TCPServer(("", self.port), MetadataHandler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True

    def metadata(self, metadata):
        MetadataHandler.set_metadata(metadata)
