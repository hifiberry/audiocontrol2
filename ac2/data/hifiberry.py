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

from ac2.data.coverarthandler import best_picture_url
from ac2.http import retrieve_url

def hifiberry_cover(song_mbid, album_mbid):
    logging.debug("trying to find coverart for %s from hifiberry", song_mbid)

    try:
        url = "https://musicdb.hifiberry.com/cover/{}/{}".format(song_mbid, album_mbid)
        cover_url = retrieve_url(url)
        if cover_url is None or len(cover_url == 0):
            return None
        else:
            return cover_url
    except Exception as e:
        logging.warn("can't load cover for %s: %s", song_mbid, e)


def enrich_metadata(metadata):
    
    if metadata.mbid is None:
        return
    
    artUrl = hifiberry_cover(metadata.mbid, metadata.albummbid)

    # check if the cover is improved
    key=metadata.songId()
    metadata.externalArtUrl = best_picture_url(key, artUrl)