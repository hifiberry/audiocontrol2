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

from ac2.data.coverarthandler import best_picture_url, best_picture_size
from ac2.simple_http import retrieve_url, post_data

BASE_URL="https://musicdb.hifiberry.com"

def cloud_url(path):
    return BASE_URL + "/"+path

def hifiberry_cover(song_mbid, album_mbid, artist_mbid, player="unknown"):
    logging.debug("trying to find coverart for %s from hifiberry", song_mbid)

    try:
        url = "{}/cover/{}/{}/{}/{}".format(BASE_URL, song_mbid, album_mbid, artist_mbid, player)
        cover_data = retrieve_url(url)
        if cover_data is None:
            return (None, 0, 0)
        else:
            cover_data = cover_data.text
        
        if cover_data is not None and len(cover_data)>0:
            try:
                (cover_url, width, height) = cover_data.split("|")
            except:
                cover_url = None
                width = 0
                height = 0
            if cover_url=="":
                cover_url = None
                
            if cover_url is None:
                logging.info("no cover found on hifiberry musicdb")
            return (cover_url, int(width), int(height))
        
        else:
            logging.info("did not receive cover data from %s", url)
            return (None, 0, 0)
            
    except Exception as e:
        logging.warn("can't load cover for %s: %s", song_mbid, e)
        logging.exception(e)
        return (None, 0, 0)
    

def send_update(metadata):
    if metadata.hifiberry_cover_found:
        return 
    
    if metadata.mbid is None:
        return
    
    key="update"+metadata.songId()
    
    best_picture_url(key, metadata.externalArtUrl)
    artUrl = best_picture_url(key, metadata.artUrl)
    
    if artUrl is not None:
        (width, height) = best_picture_size(key)
    else:
        return
    
    if metadata.albummbid is not None:
        mbid = metadata.albummbid
    else:
        mbid = metadata.mbid
    
    data = {
        "mbid": mbid,
        "url": artUrl,
        "width": width,
        "height": height
        }
    
    try:
        logging.info("sending cover update to hifiberry musicdb")
        url = "{}/cover-update".format(BASE_URL)
        post_data(url,data)
    except Exception as e:
        logging.exception(e)
    
    

def enrich_metadata(metadata):
    
    if metadata.mbid is None:
        return
    
    (artUrl, width, height) = hifiberry_cover(
        metadata.mbid, 
        metadata.albummbid, 
        metadata.artistmbid,
        metadata.playerName)
    
    # check if the cover is improved
    key=metadata.songId()
    metadata.externalArtUrl = best_picture_url(key, artUrl, width, height)
    
    if metadata.externalArtUrl == artUrl and artUrl is not None:
        metadata.hifiberry_cover_found = True
    
    
    