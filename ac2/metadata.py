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

lastfmuser = None


def set_lastfmuser(username):
    global lastfmuser
    lastfmuser = username


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
        self.artistmbid = None
        self.albummbid = None
        self.loved = None
        self.wiki = None
        self.loveSupported = False
        self.tags = None

    def sameSong(self, other):
        if not isinstance(other, Metadata):
            return False

        return self.artist == other.artist and \
            self.title == other.title

    def sameArtwork(self, other):
        if not isinstance(other, Metadata):
            return False

        return self.artUrl == other.artUrl

    def __eq__(self, other):
        if not isinstance(other, Metadata):
            return False

        return self.artist == other.artist and \
            self.title == other.title and \
            self.artUrl == other.artUrl and \
            self.albumTitle == other.albumTitle and \
            self.playerName == other.playerName and \
            self.playerState == other.playerState

    def __ne__(self, other):
        if not isinstance(other, Metadata):
            return True

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

album_template = "http://ws.audioscrobbler.com/2.0/?" \
    "method=album.getInfo&api_key=7d2431d8bb5608574b59ea9c7cfe5cbd" \
    "&artist={}&album={}&format=json"


def enrich_metadata_from_lastfm(metadata):
    logging.debug("enriching metadata")

    userparam = ""
    if lastfmuser is not None:
        userparam = "&user={}".format(quote(lastfmuser))
        metadata.loveSupported = True
        logging.debug("Love supported")
    else:
        logging.debug("Love unsupported")

    trackdata = None
    albumdata = None

    # Get track data
    if metadata.artist is not None and \
            metadata.title is not None:
        trackdata = trackInfo(metadata.artist, metadata.title, userparam)

    # Try to get a album cover
    if metadata.artUrl is None:
        # Get album data if album is set
        if metadata.artist is not None and \
                metadata.albumTitle is not None:
            albumdata = albumInfo(metadata.artist, metadata.albumTitle)

        if albumdata is not None:
            metadata.artUrl = bestImage(albumdata)
            logging.info("Got album cover for %s/%s from Last.FM: %s",
                         metadata.artist, metadata.albumTitle,
                         metadata.artUrl)

    # Update track with more information
    if trackdata is not None and "track" in trackdata:

        trackdata = trackdata["track"]

        if metadata.artistmbid is None:
            if "artist" in trackdata and "mbid" in trackdata["artist"]:
                    metadata.artistmbid = trackdata["artist"]["mbid"]
                    logging.debug("artistmbid=%s", metadata.artistmbid)

        if metadata.albummbid is None:
            if "album" in trackdata and "mbid" in trackdata["album"]:
                    metadata.artistmbid = trackdata["album"]["mbid"]
                    logging.debug("albummbid=%s", metadata.artistmbid)

        if metadata.artUrl is None:

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
            logging.debug("not updating artUrl as it exists for %s/%s",
                          metadata.artist, metadata.title)

        if metadata.playCount is None and "userplaycount" in trackdata:
            metadata.playCount = trackdata["userplaycount"]

        if metadata.mbid is None and "mbid" in trackdata:
            metadata.mbid = trackdata["mbid"]
            logging.debug("mbid=%s", metadata.mbid)

        if metadata.mbid is None and "mbid" in trackdata:
            metadata.mbid = trackdata["mbid"]
            logging.debug("mbid=%s", metadata.mbid)

        if metadata.loved is None and "userloved" in trackdata:
            metadata.loved = (int(trackdata["userloved"]) > 0)

        if metadata.wiki is None and "wiki" in trackdata:
            metadata.wiki = trackdata["wiki"]
            logging.debug("found Wiki entry")

        if metadata.tags is None and "toptags" in trackdata:
            tags = []
            for tag in trackdata["toptags"]["tag"]:
                tagname = tag["name"]
                tags.append(tagname.lower())
            logging.debug("adding tags from Last.FM: %s", tags)
            metadata.tags = tags

    else:
        logging.info("no track data for %s/%s on Last.FM",
                     metadata.artist,
                     metadata.title)


def trackInfo(artist, title, userparam):

        key = "track/{}/{}".format(artist, title)
        trackdata = lastfmcache.get(key)

        if trackdata is not None:
            logging.debug("Found cached entry for %s", key)
        else:
            try:
                if negativeCache.get(key) is None:
                    url = track_template.format(quote(artist),
                                                quote(title),
                                                userparam)
                    with urlopen(url) as connection:
                        trackdata = json.loads(connection.read().decode())
                    lastfmcache[key] = trackdata
            except Exception as e:
                logging.warning("Last.FM exception %s", e)
                negativeCache[key] = True

        return trackdata


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
                lastfmcache[key] = artist_data
        except Exception as e:
            logging.warning("Last.FM exception %s", e)
            negativeCache[key] = True

    return artist_data


def albumInfo(artist_name, album_name):

    key = "album/{}/{}".format(artist_name, album_name)
    album_data = lastfmcache.get(key)

    if album_data is not None:
        logging.debug("Found cached entry for %s", key)
    else:
        try:
            if negativeCache.get(key) is None:
                url = album_template.format(quote(artist_name),
                                            quote(album_name))
                with urlopen(url) as connection:
                    album_data = json.loads(connection.read().decode())
                lastfmcache[key] = album_data
        except Exception as e:
            logging.warning("Last.FM exception %s", e)
            negativeCache[key] = True

    return album_data


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

