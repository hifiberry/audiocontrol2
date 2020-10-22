'''
Copyright (c) 2020 Modul 9/HiFiBerry

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

from expiringdict import ExpiringDict

import ac2.data.musicbrainz as musicbrainz
import ac2.data.lastfm as lastfmdata
import ac2.data.fanarttv as fanarttv
import ac2.data.hifiberry as hifiberrydb
import ac2.data.coverartarchive as coverartarchive
from ac2.data.identities import host_uuid
from ac2.data.guess import guess_order, guess_stream_order, \
    ORDER_ARTIST_TITLE, ORDER_TITLE_ARTIST, ORDER_ARTIST_TITLE

# Use external metadata?
external_metadata = True

order_cache = ExpiringDict(max_len=10, max_age_seconds=3600)

class Metadata:
    """
    Class to start metadata of a song
    """

    loveSupportedDefault = False

    def __init__(self, artist=None, title=None,
                 albumArtist=None, albumTitle=None,
                 artUrl=None,
                 discNumber=None, trackNumber=None,
                 playerName=None, playerState="unknown",
                 streamUrl=None):
        self.artist = artist
        self.title = title
        self.albumArtist = albumArtist
        self.albumTitle = albumTitle
        self.artUrl = artUrl
        self.externalArtUrl = None
        self.discNumber = discNumber
        self.tracknumber = trackNumber
        self.playerName = playerName
        self.playerState = playerState
        self.streamUrl = streamUrl
        self.playCount = None
        self.mbid = None
        self.artistmbid = None
        self.albummbid = None
        self.loved = None
        self.wiki = None
        self.loveSupported = Metadata.loveSupportedDefault
        self.tags = []
        self.skipped = False
        self.host_uuid = None
        self.releaseDate = None
        self.trackid = None
        self.hifiberry_cover_found=False
        self.duration=0
        self.time=0

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

    def fix_problems(self, guess=True):
        """
        Cleanup metadata for known problems
        """
        
        # MPD web radio stations use different schemes to encode
        # artist and title into a title string
        # we try to guess here what's used
        if (self.artist_unknown() and 
            self.title is not None):
            
            if (" - " in self.title):
                [data1, data2] = self.title.split(" - ", 1)
            elif (", " in self.title):
                [data1, data2] = self.title.split(", ", 1)
            else:
                data1=""
                data2=""

            data1=data1.strip()
            data2=data2.strip()
            
            if len(data2) > 0:
                
                cached_order = order_cache.get(data1+"/"+data2,-1)
            
                if cached_order>=0:
                    order = cached_order
                elif not(guess) or not(external_metadata):
                    order = ORDER_ARTIST_TITLE
                else:
                    if self.streamUrl is not None and self.streamUrl.startswith("http"):
                        order = guess_stream_order(self.streamUrl, data1, data2)
                    else:
                        order = guess_order(data1, data2)
                        
                if order == ORDER_TITLE_ARTIST:
                    self.title = data1
                    self.artist = data2
                else:
                    self.artist = data1
                    self.title = data2

                order_cache[data1+"/"+data2] = order



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

    def is_unknown(self):
        if self.artist_unknown() or self.title_unknown():
            return True

        return False
    
    def artist_unknown(self):
        if str(self.artist).lower() in ["","none","unknown","unknown artist"]:
            return True
        else:
            return False
        
    def title_unknown(self):
        if str(self.title).lower() in ["","none","unknown","unknown title","unknown song"]:
            return True
        else:
            return False

    def songId(self):
        return "{}/{}".format(self.artist, self.title)
    
    def __str__(self):
        return "{}: {} ({}) {}".format(self.artist, self.title,
                                       self.albumTitle, self.artUrl)


def enrich_metadata(metadata, callback=None):
    """
    Add more metadata to a song based on the information that are already
    given. These will be retrieved from external sources.
    """
    songId = metadata.songId()

    if external_metadata:

        metadata.host_uuid = host_uuid()
        
        # Try musicbrainzs first
        try:
            musicbrainz.enrich_metadata(metadata)
        except Exception as e:
            logging.warn("error when retrieving data from musicbrainz")
            logging.exception(e)
            
        # Then HiFiBerry MusicDB
        try:
            hifiberrydb.enrich_metadata(metadata)
        except Exception as e:
            logging.warn("error when retrieving data from hifiberry db")
            logging.exception(e)

        # Then Last.FM
        try:
            lastfmdata.enrich_metadata(metadata)
        except Exception as e:
            logging.warn("error when retrieving data from last.fm")
            logging.exception(e)
                
        # try Fanart.TV, but without artist picture
        try:
            fanarttv.enrich_metadata(metadata, allow_artist_picture=False)
        except Exception as e:
            logging.exception(e)
        
        # try coverartarchive
        try:
            coverartarchive.enrich_metadata(metadata)
        except Exception as e:
            logging.exception(e)
            
        hifiberrydb.send_update(metadata)
        
        # still no cover? try to get at least an artist picture
        try:
            fanarttv.enrich_metadata(metadata, allow_artist_picture=True)
        except Exception as e:
            logging.exception(e)
    
    if callback is not None:
        callback.update_metadata_attributes(metadata.__dict__, songId)

 
def enrich_metadata_bg(metadata, callback):
    md = metadata.copy()
    threading.Thread(target=enrich_metadata, args=(md, callback)).start()

