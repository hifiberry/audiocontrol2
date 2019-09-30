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
from time import sleep
import logging
from expiringdict import ExpiringDict
import json
from urllib.parse import quote
from urllib.request import urlopen


lastfmuser = None


class Metadata:
    """
    Class to start metadata of a song
    """

    def __init__(self, artist=None, title=None,
                 albumArtist=None, albumTitle=None,
                 artUrl=None,
                 discNumber=None, trackNumber=None,
                 playerName=None, playerState="unknown"):
        self.artist = artist
        self.title = title
        self.albumArtist = albumArtist
        self.albumTitle = albumTitle
        self.artUrl = artUrl
        self.discNumber = discNumber
        self.tracknumber = trackNumber
        self.playerName = playerName
        self.playerState = playerState
        self.playCount = None
        self.mbid = None
        self.loved = None
        self.wiki = None

    def sameSong(self, other):
        if not isinstance(other, Metadata):
            return NotImplemented

        return self.artist == other.artist and \
            self.title == other.title

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
            self.albumTitle == other.albumTitle and \
            self.playerName == other.playerName and \
            self.playerState == other.playerState

    def __ne__(self, other):
        if not isinstance(other, Metadata):
            return NotImplemented

        return not(self.__eq__(other))

    def fixProblems(self):
        """
        Cleanup metadata for known problems
        """

        # MPD web radio stations use different schemes to encode
        # artist and title into a title string
        # we try to guess here what's used
        if (self.playerName == "mpd") and \
                (self.artist == "unknown artist"):
            if (" - " in self.title):
                [artist, title] = self.title.split(" - ", 1)
                self.artist = artist
                self.title = title
            if (", " in self.title):
                [title, artist] = self.title.split(", ", 1)
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
                  "file://unknown.png",
                  None,
                  None,
                  None,
                  None
                  ]
        songs = [
            ["Madonna", "Like a Virgin"],
            ["Rammstein", "Mutter"],
            ["Iggy Pop", "James Bond"],
            ["Porcupine Tree", "Normal"],
            ["Clinton Shorter", "Truth"],
            ["Bruce Springsteen", "The River"],
            ["Plan B", "Kidz"],
            ["The Spooks", "Things I've seen"],
            ["Aldous Harding", "The Barrel"]
        ]

        states = ["playing", "paused", "stopped"]

        while not(self.stop):

            coverindex = random.randrange(len(covers))
            songindex = random.randrange(len(songs))
            stateindex = random.randrange(len(states))

            md = Metadata(artist=songs[songindex][0],
                          title=songs[songindex][1],
                          artUrl=covers[coverindex],
                          playerName="dummy",
                          playerState=states[stateindex])
            if self.display is not None:
                self.display.notify(md)

            sleep(self.interval)

    def stop(self):
        self.stop = True


def enrich_metadata(metadata):
    enrich_metadata_from_lastfm(metadata)


lastfmcache = ExpiringDict(max_len=100,
                           max_age_seconds=600)
negativeCache = ExpiringDict(max_len=100,
                             max_age_seconds=600)

urltemplate = "http://ws.audioscrobbler.com/2.0/?" \
    "method=track.getInfo&api_key=7d2431d8bb5608574b59ea9c7cfe5cbd" \
    "&artist={}&track={}&format=json{}"


def enrich_metadata_from_lastfm(metadata):
    logging.debug("enriching metadata")

    userparam = ""
    if lastfmuser is not None:
        userparam = "&user={}".format(quote(lastfmuser))

    trackdata = None

    # Get last.FM data online or from cache
    if metadata.artist is not None and \
            metadata.title is not None:

        key = "track/{}/{}".format(metadata.artist, metadata.title)
        trackdata = lastfmcache.get(key)

        if trackdata is not None:
            logging.debug("Found cached entry for %s", key)
        else:
            try:
                if negativeCache.get(key) is None:
                    url = urltemplate.format(quote(metadata.artist),
                                             quote(metadata.title),
                                             userparam)
                    with urlopen(url) as connection:
                        trackdata = json.loads(connection.read().decode())
                    lastfmcache[key] = trackdata
            except Exception as e:
                logging.warning("Last.FM exception %s", e)
                negativeCache[key] = True

    if trackdata is not None and "track" in trackdata:

        trackdata = trackdata["track"]

        if metadata.artUrl is None:
            metadata.artUrl = bestImage(trackdata)
            if metadata.artUrl is not None:
                logging.info("got cover for %s/%s from Last.FM",
                             metadata.artist,
                             metadata.title)
            else:
                logging.info("no cover for %s/%s on Last.FM",
                             metadata.artist,
                             metadata.title)

        else:
            logging.debug("Not updating artUrl as it exists for %s: %s %s",
                          key, metadata.artUrl, type(metadata.artUrl))

        if metadata.playCount is None and "userplaycount" in trackdata:
            metadata.playCount = trackdata["userplaycount"]

        if metadata.mbid is None and "mbid" in trackdata:
            metadata.mbid = trackdata["mbid"]

        if metadata.loved is None and "userloved" in trackdata:
            metadata.loved = (int(trackdata["userloved"]) > 0)

        if metadata.wiki is None and "wiki" in trackdata:
            metadata.wiki = trackdata["wiki"]

    else:
        logging.info("no track data for %s/%s on Last.FM",
                     metadata.artist,
                     metadata.title)


def bestImage(lastfmdata):
    try:
        urls = lastfmdata["album"]["image"]
        res = {}
        for u in urls:
            res[u["size"]] = u["#text"]

        for size in ["extralarge", "large", "medium", "small"]:
            if size in res:
                logging.debug("found image size %s", size)
                return res[size]

        return None

    except KeyError:
        pass
