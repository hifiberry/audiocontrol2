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
from typing import Dict

from ac2.plugins.metadata import MetadataDisplay
from ac2.simple_http import post_data

ACCESS_TOKEN="ZTgxZDY3YTY0MGNhMzhmZjRlN2IzZTJmZjNmMjY5N2M3NWQwODJjYTYwZDk1ZDQxMmJlZmQzMDIxNDM5OWRhMA=="

class LaMetricPush(MetadataDisplay):
    '''
    Post metadata to a LaMetric time device
    '''

    def __init__(self, params: Dict[str, str]=None):
        super().__init__()
        self.lametric = params.get("ip", "192.168.30.120")
        self.url = "https://{}:4343/api/v1/dev/widget/update/com.lametric.b647e225d0b81484c19ff25030915e58".format(self.lametric)
        pass

    def notify(self, metadata):
        
        data = {
                "frames": [
                    {
                        "text": metadata.artist,
                        "icon": "a22046"
                    },
                    {
                        "text":metadata.title,
                        "icon": "a22046"
                    }
                ]
            }
        
        headers = {
            "X-Access-Token": ACCESS_TOKEN,
            "Accept": "application/json",
            "Cache-Control": "no-cache"
        }
        
        logging.info("sending update to LaMetric at %s", self.lametric)

        post_data(self.url, json.dumps(data), headers=headers, verify=False)
        
#
# Demo code
#
        
def demo():
    from ac2.metadata import Metadata
    lp = LaMetricPush({"ip":"192.168.30.120"})
    md = Metadata(artist="artist-demo", title="title_demo")
    lp.notify(md)
      
if __name__== "__main__":
    demo()       

