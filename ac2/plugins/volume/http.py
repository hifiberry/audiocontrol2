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

import requests
import logging


class VolumeHTTPRequest():
    '''
    Post volume via HTTP
    '''

    def __init__(self, url=None, request_type="json"):
        super()
        self.request_type = request_type
        self.url = url
        pass

    def notify_volume(self, volume_percent):

        if (self.request_type == "json"):
            try:
                r = requests.post(self.url, json={"percent":volume_percent})
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
