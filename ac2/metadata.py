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

import copy
import threading
import logging

import ac2.data.lastfm as lastfmdata
import ac2.data.coverartarchive as coverart


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
        self.tags = []
        self.skipped = False

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

    def fill_undefined(self, metadata):
        for attrib in metadata.__dict__:
            if attrib in self.__dict__ and self.__dict__[attrib] is None:
                self.__dict__[attrib] = metadata.__dict__[attrib]

    def add_tag(self, tag):
        tag = tag.lower().replace("-", " ")
        if not tag in self.tags:
            self.tags.append(tag)

    def copy(self):
        return copy.copy(self)

    def __str__(self):
        return "{}: {} ({}) {}".format(self.artist, self.title,
                                       self.albumTitle, self.artUrl)


class MetadataDisplay:

    def __init__(self):
        pass

    def notify(self, metadata):
        raise RuntimeError("notify not implemented")


def enrich_metadata(metadata, callback=None):
    """
    Add more metadata to a song based on the information that are already
    given. These will be retrieved from external sources.
    """
    lastfmdata.enrich_metadata_from_lastfm(metadata)

    if metadata.albummbid is not None and metadata.artUrl is None:
        # Try to get cover from coverartarchive
        metadata.artUrl = coverart.coverartarchive_cover(metadata.albummbid)

    if callback is not None:
        callback.update_metadata_attributes(metadata.__dict__)


def enrich_metadata_bg(metadata, callback):

    logging.debug("metadata updater thread 1")

    md = metadata.copy()
    threading.Thread(target=enrich_metadata, args=(md, callback)).start()
    logging.debug("metadata updater thread 2")

