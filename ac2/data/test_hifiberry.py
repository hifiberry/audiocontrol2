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
import unittest
from time import sleep

from ac2.metadata import Metadata
from ac2.data import hifiberry


class Test(unittest.TestCase):

    def test_get_cover(self):
        md = Metadata()
        # A Rush of Blood to the Head, Coldplay
        md.artist="Coldplay"
        md.mbid="58b961e1-a2ef-4e92-a82b-199b15bb3cd8"
        md.albummbid = "219b202d-290e-3960-b626-bf852a63bc50"
        self.assertIsNone(md.artUrl)
        self.assertIsNone(md.externalArtUrl)
   
        hifiberry.enrich_metadata(md)
        # Cover might be be in cache at the HiFiBerry musicdb,
        # in this case try again a few seconds later
        if md.externalArtUrl is None:
            sleep(5)
            hifiberry.enrich_metadata(md)

        self.assertIsNone(md.artUrl)
        self.assertIsNotNone(md.externalArtUrl)


if __name__ == "__main__":
    unittest.main()