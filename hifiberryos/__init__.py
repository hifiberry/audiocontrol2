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
import logging


def hifiberry_conf():
    if os.path.exists("/boot/hifiberry.conf"):
        return "/boot/hifiberry.conf"
    else:
        return "/etc/hifiberry.conf"


def hifiberry_config():
    conf_file = hifiberry_conf()
    try:
        return read_simple_config(conf_file)
    except IOError as e:
        logging.warn("could not read %s (%s)", conf_file, e)
        return {}


def read_simple_config(filename):
    res = {}
    with open(filename, "r") as ins:
        for line in ins:
            if "=" in line:
                [attrib, val] = line.split("=", 1)
                attrib = attrib.strip()
                val = val.strip()
                if val[0] == '"' and val[len(val) - 1] == '"':
                    val = val[1:-1]
                res[attrib] = val

    print(res)
    return res
