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

import os
import time
import re

from hifiberryos import hifiberry_config

ETH = "ethernet"
WLAN = "wlan"

if "DEV" in os.environ:
    development_mode = True
else:
    development_mode = False

if development_mode:
    interface_names = {
        ETH: "en0",
        WLAN: "en1"
    }
else:
    interface_names = {
        ETH: "eth0",
        WLAN: "wlan0"
    }


def get_current_config():
    res = {
        ETH: get_network(interface_names[ETH]),
        WLAN: get_network(interface_names[WLAN])
    }

    config = hifiberry_config()
    res[ETH]["enabled"] = config.get("eth_enable", 1)
    res[WLAN]["enabled"] = config.get("wifi_enable", 0)
    res[WLAN]["ssid"] = config.get("wifi_ssid", "")
    res[WLAN]["psk"] = config.get("wifi_psk", "")
    res[WLAN]["country"] = config.get("wifi_country", "")
    return res


def get_network(ifname):
    res = {"state": "inactive"}
    from netifaces import interfaces, ifaddresses, AF_INET
    if ifname not in interfaces():
        return res

    addrs = ifaddresses(ifname)
    if AF_INET in addrs:
        res["state"] = "active"
        res.update(addrs[AF_INET][0])

    return res


def find_networks():
    if development_mode:
        time.sleep(1)
        res = '''          Cell 02 - Address: BB:66:77:88:99:AA
                    Quality=67/70  Signal level=-43 dBm  
                    ESSID:"guest"
          Cell 03 - Address: 11:22:33:FF:33:11
                    Channel:6
                    Frequency:2.437 GHz (Channel 6)
                    Quality=52/70  Signal level=-58 dBm  
                    ESSID:"don't know anything"'''
    else:
        import subprocess
        res = subprocess.check_output(['iwlist', 'scan']).decode("utf-8")

    essid_re = 'ESSID:\"(.*)\"'
    quality_re = "Quality=([0-9]+)/([0-9]+)"

    ssids = {}
    ssid = None
    quality = 0
    for line in res.splitlines():
        ssid_match = re.search(essid_re, line)
        if ssid_match is not None:
            ssid = ssid_match.group(1)

        quality_match = re.search(quality_re, line)
        if quality_match is not None:
            q1 = quality_match.group(1)
            q2 = quality_match.group(2)
            quality = float(q1) / float(q2)

        if ssid is not None:
            ssids[ssid] = quality
            quality = 0
            ssid = None

    return ssids


def configure_wifi(ssid, psk, countrycode, enable=True):
    pass
