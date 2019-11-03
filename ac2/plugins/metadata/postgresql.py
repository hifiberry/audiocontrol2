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

from datetime import datetime, timedelta
import logging

from ac2.metadata import MetadataDisplay
from ac2.metadata import enrich_metadata


class MetadataPostgres(MetadataDisplay):

    def __init__(self):
        super()
        self.starttimestamp = None
        self.conn = None
        self.user = None
        self.password = None
        self.host = "127.0.0.1"
        self.database = "hifiberry"
        self.table = "scrobbles"
        self.currentmetadata = None

    def notify(self, metadata):

        if metadata.sameSong(self.currentmetadata):
            # This is still the same song, but some information might have
            # been updated
            self.currentmetadata = metadata
            if metadata.playerState == "playing":
                logging.debug("metadata updated, but not yet saved")
                return

        # Build dict and store it to database
        if self.currentmetadata is not None:
            enrich_metadata(self.currentmetadata)
            songdict = self.currentmetadata.__dict__

            # Some fields are not needed
            for attrib in ["wiki", "loveSupported"]:
                if attrib in songdict:
                    del songdict[attrib]

            songdict["started"] = self.starttimestamp.isoformat()
            songdict["finished"] = datetime.now().isoformat()

            # If a song had been played for less than 10 seconds mark
            # is as "skipped"
            if (datetime.now() - self.starttimestamp) < timedelta(seconds=10):
                songdict["skipped"] = True

            logging.debug("saving metadata to postgresql")
            self.write_metadata(songdict)

        logging.debug("started listening to a new song")
        self.currentmetadata = metadata
        self.starttimestamp = datetime.now()

    def write_metadata(self, songdict):
        try:

            if songdict is None:
                return

            if songdict.get("artist") is None or songdict.get("title") is None:
                logging.debug("undefined artist/title, won't store in db")

            from psycopg2.extras import Json
            conn = self.db_connection()
            if conn is None:
                logging.info("not connected to database, not scrobbling")

            cur = conn.cursor()
            logging.debug("inserting %s", songdict)
            cur.execute("INSERT INTO scrobbles (songdata) VALUES (%s)",
                        [Json(songdict)])
            conn.commit()
            cur.close()

        except Exception as e:
            logging.warn("can't write to database: %s", e)
            self.conn = None

    def db_connection(self):
        try:
            import psycopg2
            if self.conn is not None:
                return self.conn

            if self.user is not None and self.password is not None:
                self.conn = psycopg2.connect(dbname=self.database,
                                             user=self.user,
                                             password=self.password,
                                             host=self.host)
            else:
                logging.warn("username and/or password missing for db connection")

        except Exception as e:
            logging.warn("can't connect to postgresql: %s", e)
            self.conn = None

        return self.conn

    def __str__(self):
        return "postgres@{}".format(self.host)
