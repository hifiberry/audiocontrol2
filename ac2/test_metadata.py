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

from ac2.metadata import Metadata, enrich_metadata


    

class MetaDataTest(unittest.TestCase):

    md_updated = False

    def test_init(self):
        md = Metadata(
            artist="artist", 
            title="title",
            albumArtist="albumartist", 
            albumTitle="albumtitle",
            artUrl="http://test",
            discNumber=1, 
            trackNumber=2,
            playerName="player", 
            playerState="unknown",
            streamUrl="http://stream")
        self.assertEqual(md.artist, "artist")
        self.assertEqual(md.title, "title")
        self.assertEqual(md.albumArtist, "albumartist")
        self.assertEqual(md.albumTitle, "albumtitle")
        self.assertEqual(md.artUrl, "http://test")
        self.assertEqual(md.externalArtUrl, None)
        self.assertEqual(md.discNumber, 1)
        self.assertEqual(md.tracknumber, 2)
        self.assertEqual(md.playerName, "player")
        self.assertEqual(md.playerState, "unknown")
        
        
    def test_same_song(self):
        md1=Metadata("artist1","song1")
        md2=Metadata("artist1","song1", albumTitle="album1")
        md3=Metadata("artist1","song1", albumTitle="album2")
        md4=Metadata("artist2","song1")
        md5=Metadata("","song1")
        
        self.assertTrue(md1.sameSong(md2))
        self.assertTrue(md1.sameSong(md3))
        self.assertTrue(md2.sameSong(md3))

        self.assertFalse(md1.sameSong(md4))
        self.assertFalse(md1.sameSong(md5))
        
        
    def test_same_artwork(self):
        md1=Metadata("artist1","song1")
        md1.artUrl = "http://art1"

        md2=Metadata("artist1","song1")
        md2.artUrl = "http://art1"
        md2.externalArtUrl = "http://art2"
        
        md3=Metadata("artist1","song1")
        md3.artUrl = "http://art3"
        md3.externalArtUrl = "http://art1"
        
        self.assertTrue(md1.sameArtwork(md1))
        self.assertTrue(md1.sameArtwork(md2))
        self.assertFalse(md1.sameArtwork(md3))
        self.assertFalse(md2.sameArtwork(md3))
        
    def test_tags(self):
        
        md1=Metadata("artist1","song1")
        md1.add_tag("tag1")
        md1.add_tag("tag2")
        md1.add_tag("tag3")
        
        self.assertIn("tag1", md1.tags)
        self.assertIn("tag2", md1.tags)
        self.assertIn("tag3", md1.tags)
        
    def test_song_id(self):
        md1=Metadata("artist1","song1",albumTitle="abum1")
        md2=Metadata("artist1","song1",albumTitle="abum2")
        md3=Metadata("artist2","song1")
        md4=Metadata("artist2","song1",albumTitle="abum1")
        
        self.assertEqual(md1.songId(),md2.songId())
        self.assertEqual(md3.songId(),md4.songId())
        self.assertNotEqual(md1.songId(),md3.songId())
        self.assertNotEqual(md2.songId(),md3.songId())
        self.assertNotEqual(md1.songId(),md4.songId())
        
        
    def test_unknown(self):
        
        md1=Metadata()
        md2=Metadata("","")
        md3=Metadata("None","None")
        md4=Metadata("unknown artist","unknown title")
        md5=Metadata("unknown","unknown")
        md6=Metadata("artist","")
        md7=Metadata(None,"name")
        md8=Metadata("Unknown","song")
        md9=Metadata("artist","unknown")
        md10=Metadata("artist","unknown song")
        md11=Metadata("artist","songs")
        
        self.assertTrue(md1.is_unknown())
        self.assertTrue(md2.is_unknown())
        self.assertTrue(md3.is_unknown())
        self.assertTrue(md4.is_unknown())
        self.assertTrue(md5.is_unknown())
        self.assertFalse(md6.is_unknown())
        self.assertFalse(md7.is_unknown())
        self.assertFalse(md8.is_unknown())
        self.assertFalse(md9.is_unknown())
        self.assertFalse(md10.is_unknown())
        self.assertFalse(md11.is_unknown())
        
        
    def test_enrich(self):
        # We should be able to get some metadata for this one
        md=Metadata("Bruce Springsteen","The River")
        self.md_updated = False
        self.updates = None
        song_id = md.songId()
        self.song_id = None
        
        self.assertIsNone(md.artUrl)
        self.assertIsNone(md.externalArtUrl)
        self.assertFalse(MetaDataTest.md_updated)
        enrich_metadata(md, callback=self)
        
        self.assertIsNotNone(md.externalArtUrl)       
        self.assertIsNotNone(md.mbid)
        self.assertIsNotNone(self.updates)
        self.assertIn("externalArtUrl", self.updates)
        self.assertIn("mbid",self.updates)
        self.assertIn("artistmbid",self.updates)
        self.assertIn("albummbid",self.updates)
        self.assertEqual(self.song_id, song_id)
        
    def update_metadata_attributes(self, updates, song_id):
        self.updates = updates
        self.song_id = song_id

if __name__ == "__main__":
    unittest.main()