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

from ac2.data.musicbrainz import track_data
from ac2.data.hifiberry import cloud_url
from ac2.simple_http import retrieve_url, post_data

ORDER_UNKNOWN = 0
ORDER_TITLE_ARTIST = 1
ORDER_ARTIST_TITLE = 2

verbose = {
    ORDER_UNKNOWN:      "unknown",
    ORDER_TITLE_ARTIST: "title/artist",
    ORDER_ARTIST_TITLE: "artist/title",
    }

stream_stats = {}

CACHE_PATH = "radio/stream-order"

def guess_stream_order(stream, field1, field2, use_cloud=True):
    MIN_STAT_RATIO = 0.1
    MIN_STATS=10
    
    if stream.startswith("http"):
        caching_supported = True
    else:
        caching_supported = False
        logging.warn("not a web radio stream, won't use caching")
    
    stats = stream_stats.get(stream,{"ta": 0, "at": 0, "order": ORDER_UNKNOWN, "cloud": ORDER_UNKNOWN})
    
    at = stats["at"]
    ta = stats["ta"]
    cloud = stats["cloud"]
    
    if stats["order"] != ORDER_UNKNOWN:
        return stats["order"]
    if stats["cloud"] != ORDER_UNKNOWN:
        return stats["cloud"]
    
    # Check hifiberry cloud if order is known for this stream
    if caching_supported:
        try:
            cacheinfo = retrieve_url(cloud_url(CACHE_PATH), 
                                     params = { 'stream' : stream })
            if cacheinfo is not None:
                cloud = int(cacheinfo.content)
            else:
                cloud = ORDER_UNKNOWN
        except Exception as e:
            logging.exception(e)
        
    if cloud in [ ORDER_ARTIST_TITLE, ORDER_TITLE_ARTIST]:
        order = cloud
        stream_order = cloud
    else:
        stream_order = ORDER_UNKNOWN
        order = guess_order(field1, field2)
    
    if order == ORDER_ARTIST_TITLE:
        at += 1
    elif order == ORDER_TITLE_ARTIST:
        ta += 1
        
    logging.debug("at/ta: %s/%s",at,ta)
        
    if stream_order == ORDER_UNKNOWN and at+ta > MIN_STATS:
        if float(at)*MIN_STAT_RATIO > ta:
            stream_order = ORDER_ARTIST_TITLE
        elif float(ta)*MIN_STAT_RATIO > at:
            stream_order = ORDER_TITLE_ARTIST
        else:
            stream_order = ORDER_UNKNOWN
        
        logging.info("guess stream %s is using %s encoding (%s/%s)",
                     stream, verbose[stream_order], at, ta)
        
        if use_cloud and caching_supported and stream_order != ORDER_UNKNOWN:
            post_data(cloud_url(CACHE_PATH), 
                      { "stream": stream,
                       "order": stream_order})
    else:
        stream_order = ORDER_UNKNOWN
            
    stream_stats[stream]={"order": stream_order, "ta": ta, "at": at, "cloud": cloud}
    return order
    

def guess_order(field1, field2):
    
    import Levenshtein
    
    ''' 
    Try to guess which field is artist and which is title
    Uses musicbrainz
    '''
    
    data_at = track_data(field2, field1)
    o_at = "{} / {}".format(field1, field2)
    v_at = "{} / {}".format(_artist(data_at),_title(data_at))
    d_at = Levenshtein.distance(o_at.lower(),v_at.lower())
    
    data_ta = track_data(field1, field2)
    o_ta = "{} / {}".format(field2, field1)
    v_ta = "{} / {}".format(_artist(data_ta),_title(data_ta))
    d_ta = Levenshtein.distance(o_ta.lower(),v_ta.lower())
    
    if (d_at == 0) and (d_ta > 0):
        return ORDER_ARTIST_TITLE
    elif (d_ta == 0) and (d_at > 0):
        return ORDER_TITLE_ARTIST
    elif (d_at+len(o_at)/4 < d_ta ):
        return ORDER_ARTIST_TITLE
    elif (d_ta+len(o_ta)/4 < d_at ):
        return ORDER_TITLE_ARTIST
    else:
        return ORDER_UNKNOWN
    
def _title(data):
    try:
        return data["title"]
    except:
        return ""
    
def _artist(data):
    try:
        return data["artist-credit"][0]["artist"]["name"]
    except:
        return ""
