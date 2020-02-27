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

import time
import logging
import datetime
from threading import Thread

from usagecollector.client import report_usage

from ac2.plugins.metadata import MetadataDisplay
import pylast

class ScrobbleSender(Thread):
    
    def __init__(self, lastfm, metadata):
        super().__init__()
        self.lastfm = lastfm
        self.metadata = metadata
    
    def run(self):
        try:
            logging.info("scrobbling " + str(self.metadata))
            unix_timestamp = int(time.mktime(
                datetime.datetime.now().timetuple()))
            self.lastfm.scrobble(
                artist=self.metadata.artist,
                title=self.metadata.title,
                timestamp=unix_timestamp)
        except Exception as e:
            logging.error("Could not scrobble %s/%s: %s",
                          self.metadata.artist,
                          self.metadata.title,
                          e)
            self.network = None
    


class LastFMScrobbler(MetadataDisplay):

    def __init__(self, api_key, api_secret,
                 username, password,
                 password_hash=None,
                 network="lastfm"):

        super().__init__()

        if password_hash is None:
            password_hash = pylast.md5(password)

        self.username = username
        self.password_hash = password_hash
        self.networkname = network.lower()
        self.api_key = api_key
        self.api_secret = api_secret

        self.current_metadata = None
        self.starttime = 0
        self.network = None

    def get_network(self):
        if self.network is not None:
            return self.network

        if self.networkname == "lastfm":
            self.network = pylast.LastFMNetwork(
                api_key=self.api_key,
                api_secret=self.api_secret,
                username=self.username,
                password_hash=self.password_hash)
        elif self.netnetworkname == "librefm":
            self.network = pylast.LibreFMNetwork(
                api_key=self.api_key,
                api_secret=self.api_secret,
                username=self.username,
                password_hash=self.password_hash)
        else:
            raise RuntimeError("Network {} unknown".format(self.networkname))

        if self.network is not None:
            self.network.enable_caching()

        return self.network

    def love(self, love):
        try:
            track = self.get_network().get_track(self.current_metadata.artist,
                                                 self.current_metadata.title)
            if love:
                logging.info("sending love to Last.FM")
                track.love()
                report_usage("audiocontrol_lastfm_love", 1)
            else:
                logging.info("sending unlove to Last.FM")
                track.unlove()
                report_usage("audiocontrol_lastfm_love", 1)
        except Exception as e:
            logging.warning("got exception %s while love/unlove", e)
            return False

        return True

    def notify(self, metadata):
        """
        Scrobble metadata of last song, store meta data of the current song
        """

        if metadata is not None and metadata.sameSong(self.current_metadata):
            self.current_metadata = metadata
            logging.debug("updated metadata for current song, not scrobbling now")
            return

        # Check if the last song was played at least 30 seconds, otherwise
        # don't scrobble it'
        now = time.time()
        listening_time = (now - self.starttime)
        lastsong_md = None

        if listening_time > 30:
            lastsong_md = self.current_metadata
        else:
            logging.debug("not yet logging %s, not listened for at least 30s",
                          lastsong_md)

        self.starttime = now
        logging.info("new song: %s", metadata)
        self.current_metadata = metadata

        if (lastsong_md is not None) and not(lastsong_md.is_unknown()):
            sender = ScrobbleSender(self.get_network(), lastsong_md)
            sender.start()
            report_usage("audiocontrol_lastfm_scrobble", 1)
        else:
            logging.info("no track data, not scrobbling %s", lastsong_md)
            

    def __str__(self):
        return "lastfmscrobbler@{}".format(self.networkname)
