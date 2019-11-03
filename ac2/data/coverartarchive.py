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
from urllib.request import urlopen
from urllib.error import HTTPError

from expiringdict import ExpiringDict

cache = ExpiringDict(max_len=100, max_age_seconds=36000)
negativeCache = ExpiringDict(max_len=100, max_age_seconds=3600)


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
    trackdata = cache.get(mbid)

    if trackdata is not None:
        logging.debug("Found cached entry for %s", mbid)
    else:
        try:
            if negativeCache.get(mbid) is None:
                url = "http://coverartarchive.org/release/{}/".format(mbid)
                with urlopen(url) as connection:
                    data = connection.read().decode()
                    trackdata = json.loads(data)
                cache[mbid] = trackdata
        except HTTPError:
            logging.debug("no cover for %s on coverartarchive", mbid)
        except Exception as e:
            logging.warning("coverart exception %s %s", type(e).__name__, e)
            negativeCache[mbid] = True

    return trackdata

