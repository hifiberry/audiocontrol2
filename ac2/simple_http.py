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

import logging
from expiringdict import ExpiringDict

import requests

from ac2.data.identities import host_uuid, release

cache = ExpiringDict(max_len=100,
                     max_age_seconds=600)
negativeCache = ExpiringDict(max_len=100,
                             max_age_seconds=600)


def clear_cache():
    cache.clear()
    negativeCache.clear()

def is_cached(url):
    return url in cache


def is_negative_cached(url):
    return url in negativeCache


def retrieve_url(url, headers = {}, verify=True, timeout=10):

    if url in cache:
        logging.debug("retrieved from cache: %s", url)
        return cache[url]
    else:
        try:
            if negativeCache.get(url) is None:
                headers['User-agent'] = 'audiocontrol/{}/{}'.format(release(), host_uuid())
                res = requests.get(url, 
                                   headers=headers, 
                                   verify=verify,
                                   timeout=timeout)
                cache[url] = res
                return res
            else:
                logging.debug("negative cache hit: %s", url)
        except Exception as e:
            logging.warning("HTTP exception while retrieving %s: %s", url, e)
            negativeCache[url] = True
            
            
def post_data(url, data, headers = {}, verify=True, timeout=10):
    
    res = None
    try:
        headers['User-agent'] = 'audiocontrol/{}/{}'.format(release(), host_uuid())
        res = requests.post(url, 
                            data = data, 
                            headers=headers, 
                            verify = verify,
                            timeout = timeout)
    except Exception as e:
        logging.warning("HTTP exception while posting %s: %s", url, e)
        
    return res