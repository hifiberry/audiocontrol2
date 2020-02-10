'''
Created on 06.02.2020

@author: matuschd
'''
import unittest

from ac2.metadata import Metadata
import ac2.data.lastfm as lastfm

class TestLastFM(unittest.TestCase):

    def test_enrich(self):
        # We should be able to get some metadata for this one
        md=Metadata("Bruce Springsteen","The River")
        lastfm.enrich_metadata(md)
        
        self.assertIsNotNone(md.externalArtUrl)
        self.assertIsNotNone(md.mbid)
        self.assertIsNotNone(md.artistmbid)


if __name__ == "__main__":
    unittest.main()