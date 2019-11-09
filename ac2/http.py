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

import logging
from urllib.request import urlopen
from expiringdict import ExpiringDict

cache = ExpiringDict(max_len=100,
                     max_age_seconds=600)
negativeCache = ExpiringDict(max_len=100,
                             max_age_seconds=600)


def retrieve_url(url):

    if url in cache:
        logging.debug("retrieved from cache: %s", url)
        return cache[url]
    else:
        try:
            if negativeCache.get(url) is None:
                with urlopen(url) as connection:
                    res = connection.read()
                    logging.debug("retrieved live version: %s", url)
                cache[url] = res
                return res
            else:
                logging.debug("negative cache hit: %s", url)
        except Exception as e:
            logging.warning("HTTP exception while retrieving %s: %s", url, e)
            negativeCache[url] = True

