'''
Created on 06.02.2020

@author: matuschd
'''
import unittest

from ac2.metadata import Metadata
from ac2.data import coverartarchive

class Test(unittest.TestCase):

    def testGetCover(self):
        md = Metadata()
        # A Rush of Blood to the Head, Coldplay
        md.albummbid = "219b202d-290e-3960-b626-bf852a63bc50"
        assert md.artUrl is None
        assert md.externalArtUrl is None
   
        coverartarchive.enrich_metadata(md)

        assert md.artUrl is None
        assert md.externalArtUrl is not None


if __name__ == "__main__":
    unittest.main()