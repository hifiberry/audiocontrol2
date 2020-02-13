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
import json
from urllib.parse import quote

from ac2.data.coverarthandler import best_picture_url
from ac2.http import retrieve_url

lastfmuser = None

track_template = "http://ws.audioscrobbler.com/2.0/?" \
    "method=track.getInfo&api_key=7d2431d8bb5608574b59ea9c7cfe5cbd" \
    "&artist={}&track={}&format=json{}"

track_mbid_template = "http://ws.audioscrobbler.com/2.0/?" \
    "method=track.getInfo&api_key=7d2431d8bb5608574b59ea9c7cfe5cbd" \
    "&mbid={}&format=json{}"

artist_template = "http://ws.audioscrobbler.com/2.0/?" \
    "method=artist.getInfo&api_key=7d2431d8bb5608574b59ea9c7cfe5cbd" \
    "&artist={}&format=json"

album_template = "http://ws.audioscrobbler.com/2.0/?" \
    "method=album.getInfo&api_key=7d2431d8bb5608574b59ea9c7cfe5cbd" \
    "&artist={}&album={}&format=json"

album_mbid_template = "http://ws.audioscrobbler.com/2.0/?" \
    "method=album.getInfo&api_key=7d2431d8bb5608574b59ea9c7cfe5cbd" \
    "&artist={}&album={}&format=json"


def set_lastfmuser(username):
    global lastfmuser
    lastfmuser = username


def enrich_metadata(metadata):
    logging.debug("enriching metadata")

    if metadata.artist is None or metadata.title is None:
        logging.debug("artist and/or title undefined, can't enrich metadata")

    userparam = ""
    if lastfmuser is not None:
        userparam = "&user={}".format(quote(lastfmuser))
        metadata.loveSupported = True
        logging.debug("Love supported")
    else:
        logging.debug("Love unsupported")

    trackdata = None
    albumdata = None

    key = metadata.songId()

    if metadata.externalArtUrl is not None:
        best_picture_url(key, metadata.externalArtUrl)

    # Get album data if album is set
    if metadata.artist is not None and \
            metadata.albumTitle is not None:
        albumdata = albumInfo(metadata.artist, metadata.albumTitle)

    found_album_cover = False
    if albumdata is not None:
        url = bestImage(albumdata)
        if url is not None:
            metadata.externalArtUrl = best_picture_url(key, url)
            logging.info("Got album cover for %s/%s from Last.FM: %s",
                         metadata.artist, metadata.albumTitle,
                         metadata.externalArtUrl)
            found_album_cover = True

        if metadata.albummbid is None:
            try:
                metadata.albummbid = albumdata["album"]["mbid"]
                logging.debug("added albummbid from Last.FM")
            except KeyError:
                # mbid might not be available
                pass

        if metadata.albumArtist is None:
            try:
                metadata.albumartist = albumdata["album"]["artist"]
                logging.debug("added album artist from Last.FM")
            except KeyError:
                # mbid might not be available
                pass

    # get track data
    if (metadata.artist is not None and metadata.title is not None) or \
        metadata.mbid is not None:

        trackdata = trackInfo(metadata.artist, metadata.title,
                              metadata.mbid, userparam)

    # Update track with more information
    if trackdata is not None and "track" in trackdata:

        trackdata = trackdata["track"]

        if metadata.artistmbid is None:
            if "artist" in trackdata and "mbid" in trackdata["artist"]:
                    metadata.artistmbid = trackdata["artist"]["mbid"]
                    logging.debug("artistmbid=%s", metadata.artistmbid)

        if metadata.albummbid is None:
            if "album" in trackdata and "mbid" in trackdata["album"]:
                    metadata.albummbid = trackdata["album"]["mbid"]
                    logging.debug("albummbid=%s", metadata.albummbid)

        if not(found_album_cover):
            url = bestImage(trackdata)
            if url is not None:
                metadata.externalArtUrl = best_picture_url(key, url)
                logging.info("Got track cover for %s/%s/%s from Last.FM: %s",
                             metadata.artist,
                             metadata.title,
                             metadata.albumTitle,
                             metadata.externalArtUrl)

        if metadata.playCount is None and "userplaycount" in trackdata:
            metadata.playCount = trackdata["userplaycount"]

        if metadata.mbid is None and "mbid" in trackdata:
            metadata.mbid = trackdata["mbid"]
            logging.debug("mbid=%s", metadata.mbid)

        if metadata.loved is None and "userloved" in trackdata:
            metadata.loved = (int(trackdata["userloved"]) > 0)

        # Workaround for "missing attribute wiki" bug
        try:
            _ = metadata.wiki
        except AttributeError:
            metadata.wiki = None
            
        if metadata.wiki is None and "wiki" in trackdata:
            metadata.wiki = trackdata["wiki"]
            logging.debug("found Wiki entry")

        if "toptags" in trackdata and "tag" in trackdata["toptags"]:
            for tag in trackdata["toptags"]["tag"]:
                metadata.add_tag(tag["name"])
                logging.debug("adding tag from Last.FM: %s", tag["name"])

    else:
        logging.info("no track data for %s/%s on Last.FM",
                     metadata.artist,
                     metadata.title)

    if metadata.artistmbid is None and metadata.artist is not None:
        artistdata = artistInfo(metadata.artist)
        if artistdata is not None:
            try:
                metadata.artistmbid = artistdata["artist"]["mbid"]
                logging.debug("added artistmbid from Last.FM")
            except KeyError:
                # mbid might not be available
                pass


def trackInfo(artist, title, mbid, userparam):

        if mbid is not None:
            url = track_mbid_template.format(mbid, userparam)
        else:
            url = track_template.format(quote(artist),
                                        quote(title),
                                        userparam)

        trackdata = None
        data = retrieve_url(url)
        if data is not None:
            trackdata = json.loads(data.text)

        if mbid is not None and (trackdata is None or "error" in trackdata):
            logging.debug("track not found via mbid, retrying with name/title")
            trackdata = trackInfo(artist, title, None, userparam)

        return trackdata


def artistInfo(artist_name):

    url = artist_template.format(quote(artist_name))
    data = retrieve_url(url)
    if data is not None:
        return json.loads(data.text)


def albumInfo(artist_name, album_name, albummbid=None):

    if albummbid is not None:
        url = album_mbid_template.format(quote(albummbid))
    else:
        url = album_template.format(quote(artist_name),
                                    quote(album_name))

    albumdata = None
    data = retrieve_url(url)
    if data is not None:
        albumdata = json.loads(data.text)

    if albummbid is not None and (albumdata is None or "error" in albumdata):
        logging.debug("album not found via mbid, retrying with name/title")
        albumdata = albumInfo(artist_name, album_name, None)

    return albumdata


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
            if size in res and len(res[size]) > 10:
                logging.debug("found image size %s: %s", size, res[size])
                return res[size]

        return None

    except KeyError:
        logging.info("couldn't find any images")
        pass
