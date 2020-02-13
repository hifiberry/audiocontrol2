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
import json

# Use caching
from ac2.simple_http import retrieve_url
from ac2.data.coverarthandler import good_enough, best_picture_url

APIKEY="749a8fca4f2d3b0462b287820ad6ab06"

def get_fanart_cover(artistmbid, albummbid, allow_artist_picture = False):
    url = "http://webservice.fanart.tv/v3/music/{}?api_key={}".format(artistmbid, APIKEY)
    try:
        json_text = retrieve_url(url).text
        if json_text is None:
            logging.debug("artist does not exit on fanart.tv")
            return 
        
        data = json.loads(json_text)
        
        # Try to find the album cover first
        try:
            coverurl = data["albums"][albummbid]["albumcover"]["url"]
            logging.debug("found album cover on fanart.tv")
            return coverurl
        except KeyError:
            logging.debug("found no album cover on fanart.tv")
        
        # If this doesn't exist, use artist cover
        if allow_artist_picture:
            try:
                imageurl = data["artistthumb"][1]["url"]
                logging.debug("found artist picture on fanart.tv")
                return imageurl
            except KeyError:
                logging.debug("found no artist picture on fanart.tv")

    
    except Exception as e:
        logging.debug("couldn't retrieve data from fanart.tv (%s)",e)


def enrich_metadata(metadata, allow_artist_picture = False):
    
    if metadata.hifiberry_cover_found:
        return
    
    if metadata.is_unknown():
        # Do not try to retrieve metadata for unknown songs
        return
    
    if metadata.artistmbid is None:
        logging.debug("artist mbid unknpown, can't use fanart.tv")
        return
    
    key = metadata.songId()
    if good_enough(key):
        logging.debug("existing cover is good enough, skipping fanart.tv")
        return
    
    url = get_fanart_cover(metadata.artistmbid, 
                           metadata.albummbid, 
                           allow_artist_picture)
    metadata.externalArtUrl = best_picture_url(key, url)