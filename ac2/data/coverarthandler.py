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
from expiringdict import ExpiringDict

covers = ExpiringDict(max_len=1000,
                      max_age_seconds=3600000)

import io
import struct
import urllib.request as urllib2


def getImageInfo(data):
    data = data
    size = len(data)
    # print(size)
    height = -1
    width = -1
    content_type = ''

    # handle GIFs
    if (size >= 10) and data[:6] in (b'GIF87a', b'GIF89a'):
        # Check to see if content_type is correct
        content_type = 'image/gif'
        w, h = struct.unpack(b"<HH", data[6:10])
        width = int(w)
        height = int(h)

    # See PNG 2. Edition spec (http://www.w3.org/TR/PNG/)
    # Bytes 0-7 are below, 4-byte chunk length, then 'IHDR'
    # and finally the 4-byte width, height
    elif ((size >= 24) and data.startswith(b'\211PNG\r\n\032\n')
          and (data[12:16] == b'IHDR')):
        content_type = 'image/png'
        w, h = struct.unpack(b">LL", data[16:24])
        width = int(w)
        height = int(h)

    # Maybe this is for an older PNG version.
    elif (size >= 16) and data.startswith(b'\211PNG\r\n\032\n'):
        # Check to see if we have the right content type
        content_type = 'image/png'
        w, h = struct.unpack(b">LL", data[8:16])
        width = int(w)
        height = int(h)

    # handle JPEGs
    elif (size >= 2) and data.startswith(b'\377\330'):
        content_type = 'image/jpeg'
        jpeg = io.BytesIO(data)
        jpeg.read(2)
        b = jpeg.read(1)
        try:
            while (b and ord(b) != 0xDA):
                while (ord(b) != 0xFF): b = jpeg.read(1)
                while (ord(b) == 0xFF): b = jpeg.read(1)
                if (ord(b) >= 0xC0 and ord(b) <= 0xC3):
                    jpeg.read(3)
                    h, w = struct.unpack(b">HH", jpeg.read(4))
                    break
                else:
                    jpeg.read(int(struct.unpack(b">H", jpeg.read(2))[0]) - 2)
                b = jpeg.read(1)
            width = int(w)
            height = int(h)
        except struct.error:
            pass
        except ValueError:
            pass

    logging.debug("parsed image")

    return content_type, width, height


class Coverart():

    def __init__(self, url, width=0, height=0):
        self.url = url
        self.width = width
        self.height = height
        self.imagedata = None

        if self.url is not None:
            if self.size() == 0:
                self.width, self.height = self.guess_size_from_url(url)

            if self.size() == 0:
                try:
                    req = urllib2.Request(url, headers={"Range": "5000"})
                    r = urllib2.urlopen(req)

                    _type, self.width, self.height = getImageInfo(r.read())
                except Exception as e:
                    logging.warning("error while parsing image from %s: %s",
                                    url, e)

        logging.debug("initialized coverart %s: %sx%s",
                      url, self.width, self.height)

    def guess_size_from_url(self, url):
        # Try to guess the size of an image based on the URL. This won't
        # be perfect, but it speeds up processing as no HTTP requests are
        # required
        if "/300x300/" in url:
            return 300, 300

        if "/150x150/" in url:
            return 300, 300

        return 0, 0

    def size(self):
        return self.width * self.height

    def __str__(self):
        return str(self.url)


def best_picture_url(key, url, width=0, height=0):
    cover = Coverart(url, width, height)
    existing_cover = covers.get(key)
    if existing_cover is not None:
        if existing_cover.size() < cover.size():
            logging.debug("%sx%s > %sx%s - using new image",
                          cover.width, cover.height,
                          existing_cover.width, existing_cover.height)
            covers[key] = cover
            return cover.url
        else:
            logging.debug("%sx%s < %sx%s - using old image",
                          cover.width, cover.height,
                          existing_cover.width, existing_cover.height)

            return existing_cover.url

    else:
        logging.debug("%sx%s, no existing image",
                      cover.width, cover.height)
        covers[key] = cover
        return cover.url

