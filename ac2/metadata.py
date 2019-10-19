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
from expiringdict import ExpiringDict
import json
from urllib.parse import quote
from urllib.request import urlopen
from pylast import Album

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
        self.loveSupported = False

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


def enrich_metadata(metadata):
    enrich_metadata_from_lastfm(metadata)


lastfmcache = ExpiringDict(max_len=100,
                           max_age_seconds=600)
negativeCache = ExpiringDict(max_len=100,
                             max_age_seconds=600)

track_template = "http://ws.audioscrobbler.com/2.0/?" \
    "method=track.getInfo&api_key=7d2431d8bb5608574b59ea9c7cfe5cbd" \
    "&artist={}&track={}&format=json{}"

artist_template = "http://ws.audioscrobbler.com/2.0/?" \
    "method=artist.getInfo&api_key=7d2431d8bb5608574b59ea9c7cfe5cbd" \
    "&artist={}&format=json"


def enrich_metadata_from_lastfm(metadata):
    logging.debug("enriching metadata")

    userparam = ""
    if lastfmuser is not None:
        userparam = "&user={}".format(quote(lastfmuser))
        metadata.loveSupported = True

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
                    url = track_template.format(quote(metadata.artist),
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


def artistInfo(artist_name):

    key = "artist/{}".format(artist_name)
    artist_data = lastfmcache.get(key)

    if artist_data is not None:
        logging.debug("Found cached entry for %s", key)
    else:
        try:
            if negativeCache.get(key) is None:
                url = artist_template.format(quote(artist_name))
                with urlopen(url) as connection:
                    artist_data = json.loads(connection.read().decode())
                return artist_data
                lastfmcache[key] = artist_data
        except Exception as e:
            logging.warning("Last.FM exception %s", e)
            negativeCache[key] = True


def bestImage(lastfmdata):
    if "album" in lastfmdata:
        key = "album"
    elif "artist" in lastfmdata:
        key = "artist"
    else:
        logging.error("can't parse lastfmdata")
        return

    try:
        urls = lastfmdata[key]["image"]
        res = {}
        for u in urls:
            res[u["size"]] = u["#text"]

        for size in ["extralarge", "large", "medium", "small"]:
            if size in res:
                logging.debug("found image size %s", size)
                return res[size]

        return None

    except KeyError:
        logging.info("couldn't find any images")
        pass

