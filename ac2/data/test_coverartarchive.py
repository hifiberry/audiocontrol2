'''
Created on 06.02.2020

@author: matuschd
'''
import unittest

from ac2.metadata import Metadata
from ac2.data import coverartarchive

class Test(unittest.TestCase):

    def test_get_cover(self):
        md = Metadata()
        # A Rush of Blood to the Head, Coldplay
        md.artist = "Coldplay"  # Necessary as unknown song won't be retrieved
        md.albummbid = "219b202d-290e-3960-b626-bf852a63bc50"
        self.assertIsNone(md.artUrl)
        self.assertIsNone(md.externalArtUrl)
   
        coverartarchive.enrich_metadata(md)

        self.assertIsNone(md.artUrl)
        self.assertIsNotNone(md.externalArtUrl)
        
    def test_unknown(self):
        md = Metadata()
        coverartarchive.enrich_metadata(md)
        
        self.assertIsNone(md.artUrl)
        self.assertIsNone(md.externalArtUrl)
   

if __name__ == "__main__":
    unittest.main()