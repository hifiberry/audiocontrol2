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

import json
import logging

from ac2.http import retrieve_url
from ac2.data.coverarthandler import good_enough, best_picture_url


def coverartarchive_cover(mbid):
    logging.debug("trying to find coverart for %s on coverartarchive", mbid)
    try:
        url = None
        covers = coverdata(mbid)
        if covers is not None:
            for img in covers["images"]:
                if img["front"]:
                    url = img["image"]
                    logging.debug("found cover from coverartarchive: %s", url)

        return url

    except Exception as e:
        logging.warn("can't load cover for %s: %s", mbid, e)


def coverdata(mbid):
    url = "http://coverartarchive.org/release/{}/".format(mbid)
    data = retrieve_url(url)
    if data is not None:
        return json.loads(data)


def enrich_metadata(metadata):
    
    if metadata.best_cover_found:
        return
    
    if metadata.albummbid is None:
        return
    key = metadata.songId()
    if good_enough(key):
        return
    
    artUrl = coverartarchive_cover(metadata.albummbid)
    # check if the cover is improved
    metadata.externalArtUrl = best_picture_url(key, artUrl)
    

"""
print(coverdata("219b202d-290e-3960-b626-bf852a63bc50"))
print(coverartarchive_cover("219b202d-290e-3960-b626-bf852a63bc50"))
"""
