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

from ac2.data.musicbrainz import track_data

ORDER_UNKNOWN = 0
ORDER_TITLE_ARTIST = 1
ORDER_ARTIST_TITLE = 2


stream_stats = {}

def guess_stream_order(stream, field1, field2):
    MIN_STAT_RATIO = 0.05
    MIN_STATS=5
    
    stats = stream_stats.get(stream,{"ta": 0, "at": 0, "order": ORDER_UNKNOWN})
    
    if stats["order"] != ORDER_UNKNOWN:
        return stats["order"]
    
    at = stats["at"]
    ta = stats["ta"]
    
    order = guess_order(field1, field2)
    
    if order == ORDER_ARTIST_TITLE:
        at += 1
    elif order == ORDER_TITLE_ARTIST:
        ta += 1
        
    if at+ta > MIN_STATS:
        if float(at)*MIN_STAT_RATIO > ta:
            stream_order = ORDER_ARTIST_TITLE
        elif float(ta)*MIN_STAT_RATIO > at:
            stream_order = ORDER_TITLE_ARTIST
        else:
            stream_order = ORDER_UNKNOWN
    else:
        stream_order = ORDER_UNKNOWN
            
    stream_stats[stream]={"order": stream_order, "ta": ta, "at": at}
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
