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

from ac2.metadata import MetadataDisplay
import pylast


class LastFMScrobbler(MetadataDisplay):

    def __init__(self, API_KEY, API_SECRET,
                 lastfm_username, lastfm_password,
                 lastfm_password_hash=None,
                 network="lastfm"):
        if lastfm_password_hash is None:
            lastfm_password_hash = pylast.md5(lastfm_password)

        network = network.lower()

        if network == "lastfm":
            self.network = pylast.LastFMNetwork(
                api_key=API_KEY,
                api_secret=API_SECRET,
                username=lastfm_username,
                password_hash=lastfm_password_hash)
        elif network == "librefm":
            self.network = pylast.LibreFMNetwork(
                api_key=API_KEY,
                api_secret=API_SECRET,
                username=lastfm_username,
                password_hash=lastfm_password_hash)
        else:
            raise RuntimeError("Network {} unknown".format(network))

        self.current_metadata = None
        self.starttime = 0

    def notify(self, metadata):
        """
        Scrobble metadata of last song, store meta data of the current song
        """

        # Check if the last song was played at least 30 seconds, otherwise
        # don't scrobble it'
        now = time.time()
        listening_time = (now - self.starttime)
        if listening_time > 30:
            md = self.current_metadata
        else:
            logging.debug("not yes logging %s, not listened for at least 30s",
                          metadata)
            md = None

        self.starttime = now
        logging.info("new metadata received: %s", metadata)
        self.current_metadata = metadata

        if (md is not None) and \
                (md.artist is not None) and \
                (md.title is not None):
            try:
                logging.info("scrobbling " + str(md))
                unix_timestamp = int(time.mktime(
                    datetime.datetime.now().timetuple()))
                self.network.scrobble(artist=md.artist,
                                      title=md.title,
                                      timestamp=unix_timestamp)
            except Exception as e:
                logging.error("Could not scrobble %s/%s: %s",
                              md.artist,
                              md.title,
                              e)

    def __str__(self):
        return "scrobbler@{}".format(self.network)
