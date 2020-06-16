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

'''
Get metadata from MPD
'''

import logging
from pathlib import Path

class MpdMetadataProcessor():
    
    def __init__(self, basedir="/"):
        self.base=Path(basedir)
        self.currentCover=None
        self.currentUrl=None
        
        
    def process_metadata(self, metadata):
        if metadata.playerName=="mpd":
            url = metadata.streamUrl
            
            if metadata.artUrl is None and url is not None:
                
                if url == self.currentUrl:
                    metadata.artUrl=self.currentCover
                else:
                    musicfile = Path(self.base, metadata.streamUrl)
                    self.currentCover=self.coverart(musicfile)
                    self.currentUrl=url
                    metadata.artUrl="file://"+str(self.currentCover)
                
                
    def coverart(self, musicfile):
        musicdir = musicfile.parents[0]
        for f in Path(musicdir).glob("*.???*"):
            for b in ["cover","front","folder"]:
                for ext in [".jpg",".jpeg",".png",".gif"]:
                    if str(f.name).lower() == b+ext:
                        return str(f)
                
