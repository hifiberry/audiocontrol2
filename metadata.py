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

from threading import Thread
from time import time, sleep


class Metadata:
    """
    Class to start metadata of a song
    """

    def __init__(self, artist=None, title=None,
                 albumArtist=None, albumTitle=None,
                 artUrl=None,
                 discNumber=None, trackNumber=None,
                 playerName=None):
        self.artist = artist
        self.title = title
        self.albumArtist = albumArtist
        self.albumTitle = albumTitle
        self.artUrl = artUrl
        self.discNumber = discNumber
        self.tracknumber = trackNumber
        self.playerName = playerName

    def sameSong(self, other):
        if not isinstance(other, Metadata):
            return NotImplemented

        return self.artist == other.artist and self.title == other.title

    def sameArtwork(self, other):
        if not isinstance(other, Metadata):
            return NotImplemented

        return self.artUrl == other.artUrl

    def __eq__(self, other):
        if not isinstance(other, Metadata):
            return NotImplemented

        return self.artist == other.artist and \
            self.title == other.title and \
            self.artUrl == other.artUrl and \
            self.albumTitle == other.albumTitle

    def __ne__(self, other):
        if not isinstance(other, Metadata):
            return NotImplemented

        return not(self.__eq__(other))

    def fixProblems(self):
        """
        Cleanup metadata for known problems
        """

        # unknown artist, but artist - title in title
        # seen on mpd web radio streams
        if (self.playerName == "mpd") and \
            (self.artist == "unknown artist") and \
                (" - " in self.title):
            [artist, title] = self.title.split(" - ", 1)
            self.artist = artist
            self.title = title

    def __str__(self):
        return "{}: {} ({}) {}".format(self.artist, self.title,
                                       self.albumTitle, self.artUrl)


class MetadataDisplay:

    def __init__(self):
        pass

    def notify(self, metadata):
        raise RuntimeError("notify not implemented")


class MetadataConsole(MetadataDisplay):

    def __init__(self):
        super()
        pass

    def notify(self, metadata):
        print("{:16s}: {}".format(metadata.playerName, metadata))

    def __str__(self):
        return "console"


class DummyMetadataCreator(Thread):
    """
    A class just use for development. It creates dummy metadata records and
    send it to the given MetadataDisplay objects
    """

    def __init__(self, display=None, interval=10):
        super().__init__()
        self.stop = False
        self.interval = interval
        self.display = display

    def run(self):
        import random

        covers = ["https://images-na.ssl-images-amazon.com/images/I/81R6Jcf5eoL._SL1500_.jpg",
                  "https://townsquare.media/site/443/files/2013/03/92rage.jpg?w=980&q=75",
                  "https://i0.wp.com/neu.rage-cover-cologne.de/wp-content/uploads/2017/12/rage-against-the-machine-ca8389d26e931c5e.jpg",
                  "https://www.rollingstone.de/wp-content/uploads/2019/04/23/11/rammstein-artwork.jpg",
                  "https://www.rammstein.de/wp-content/uploads/2010/03/5373042_sehnsucht_aec.jpg",
                  "http://1t8r984d8wic2jedckksuin1.wpengine.netdna-cdn.com/wp-content/uploads/2016/03/093624642428-1024x1024.jpg",
                  "https://streamd.hitparade.ch/cdimages/pippo_pollina-elementare_watson_a.jpg",
                  "https://media05.myheimat.de/2012/10/05/2342415_orig.jpg",
                  "file://static/unknown.png",
                  "file://static/unknown.png",
                  "file://static/unknown.png",
                  "file://static/unknown.png",
                  "file://static/unknown.png",
                  ]

        while not(self.stop):
            rnd = random.randrange(100000)

            coverindex = random.randrange(len(covers))

            md = Metadata(artist="Artist {}".format(rnd),
                          title="Title {}".format(rnd),
                          albumTitle="Album {}".format(rnd),
                          artUrl=covers[coverindex],
                          playerName="dummy")
            self.display.notify(md)
            sleep(self.interval)

    def stop(self):
        self.stop = True
