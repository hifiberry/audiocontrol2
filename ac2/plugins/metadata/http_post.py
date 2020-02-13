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

from ac2.plugins.metadata import MetadataDisplay

import requests
import logging
import os
import urllib.parse


class MetadataHTTPRequest(MetadataDisplay):
    '''
    Post metadata via HTTP
    '''

    def __init__(self, url=None, request_type="json"):
        super().__init__()
        self.request_type = request_type
        self.url = url
        pass

    def notify(self, metadata):

        localfile = None

        # enrich_metadata(metadata)

        if metadata.artUrl is not None:
            if metadata.artUrl.startswith("file://"):
                localfile = metadata.artUrl[7:]
            else:
                url = urllib.parse.urlparse(metadata.artUrl, scheme="file")
                if url.scheme == "file":
                    localfile = url.path

        if localfile is not None and os.path.isfile(localfile):
            # use only file part of path name
            metadata.artUrl = "artwork/" + \
                os.path.split(localfile)[1]

        if (self.request_type == "json"):
            try:
                r = requests.post(self.url, 
                                  json=metadata.__dict__,
                                  timeout=10)
            except Exception as e:
                logging.error("Exception when posting metadata: %s", e)
                return
        else:
            logging.error("request_type %s not supported", self.request_type)
            return

        if (r.status_code > 299) or (r.status_code < 200):
            logging.error("got HTTP error %s when posting metadata to %s",
                          r.status_code,
                          self.url)

    def __str__(self):
        return "http"
