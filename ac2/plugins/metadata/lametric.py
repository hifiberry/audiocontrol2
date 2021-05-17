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
import time
import json
from typing import Dict
from urllib.parse import urlparse
from threading import Thread

from usagecollector.client import report_usage

from ac2.plugins.metadata import MetadataDisplay
from ac2.simple_http import post_data, retrieve_url

ACCESS_TOKEN="ZTgxZDY3YTY0MGNhMzhmZjRlN2IzZTJmZjNmMjY5N2M3NWQwODJjYTYwZDk1ZDQxMmJlZmQzMDIxNDM5OWRhMA=="

class LaMetricPush(MetadataDisplay):
    '''
    Post metadata to a LaMetric time device
    '''

    def __init__(self, params: Dict[str, str]={}):
        super().__init__()
        self.set_ips(params.get("ip", ""))
        if len(self.urls)==0: 
            discover = LaMetricDiscovery(self)
            discover.start()
    
    def set_ips(self, ip_list):
        if isinstance(ip_list, str):
            ips = []
            for ip in ip_list.split(","):
                ips.append(ip.strip())
            
            ip_list = ips
            
        self.urls=[]
        for ip in ip_list:
            if len(ip)>0:
                url = "https://{}:4343/api/v1/dev/widget/update/com.lametric.b647e225d0b81484c19ff25030915e58".format(ip)
                self.urls.append(url)
                report_usage("audiocontrol_lametric_discovered", 1)
        

    def notify(self, metadata):
        if metadata.artist is None or metadata.title is None:
            logging.debug("ignoring undefined metatdata")
            return 
        
        data = {
                "frames": [
                    {
                        "text": metadata.artist+"-"+metadata.title,
                        "icon": "a22046",
                        "duration": 10000,
                    }
                ]
            }
        
        headers = {
            "X-Access-Token": ACCESS_TOKEN,
            "Accept": "application/json",
            "Cache-Control": "no-cache"
        }
        
        for url in self.urls:
            logging.info("sending update to LaMetric at %s",url)
            report_usage("audiocontrol_lametric_metadata", 1)

            post_data(url, json.dumps(data), headers=headers, verify=False)
        
    def notify_volume(self, volume):
        pass

class LaMetricDiscovery(Thread):
    
    def __init__( self, lametric ):
        super().__init__()
        self.lametric = lametric
        
        
    def my_broadcasts(self):
        import netifaces 
        res = []
        for iface in netifaces.interfaces():
            try: 
                config = netifaces.ifaddresses(iface)[netifaces.AF_INET][0]
                bcast = config["broadcast"]
                if bcast.startswith("127."):
                    continue
                logging.debug("found broadcast address %s",bcast)
                res.append(bcast)
            except:
                pass
        return res
            

    def run(self):
        import socket  
        import sys
        
        res = []
  
        for dst in self.my_broadcasts():
            st = "upnp:rootdevice"  
            if len(sys.argv) > 2:  
                st = sys.argv[2]
            msg = [  
                'M-SEARCH * HTTP/1.1',
                'Host:239.255.255.250:1900',
                'ST:%s' % (st,),
                'Man:"ssdp:discover"',
                'MX:1',
                '']
            urls = set()
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)  
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.settimeout(5)
            try:  
                s.sendto('\r\n'.join(msg).encode("utf-8"), (dst, 1900) )
            except Exception as e:
                logging.warning("Exception %s when sending to %s",e, dst)
                continue
            while True:  
                try:
                    data, _addr = s.recvfrom(32*1024)
                    for line in data.decode("utf-8").splitlines():
                        if line.startswith("LOCATION:"):
                            (_loc,url) = line.split(":",1)
                            urls.add(url.strip())
                except socket.timeout:
                    break
                
            for url in urls:
                desc = retrieve_url(url, timeout=2)
                if desc is None:
                    continue
        
                if "<deviceType>urn:schemas-upnp-org:device:LaMetric:1</deviceType>" in desc.text:
                    o = urlparse(url)
                    ip = o.hostname
                    logging.info("found LaMetric at "+ip)
                    
                    res.append(ip)
                
        self.lametric.set_ips(res)

#
# Demo code
#
        
def demo():
    from ac2.metadata import Metadata
    
    lp = LaMetricPush()
    time.sleep(15)
    md = Metadata(artist="demo artist", title="demo title")
    lp.notify(md)
      
if __name__== "__main__":
    logging.basicConfig(format='%(levelname)s: %(module)s - %(message)s',
                                level=logging.DEBUG)
    demo()       

