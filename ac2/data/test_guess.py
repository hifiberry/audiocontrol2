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
import unittest

from ac2.data.guess import ORDER_ARTIST_TITLE, ORDER_TITLE_ARTIST, ORDER_UNKNOWN, \
    guess_order, guess_stream_order
    

class TestGuess(unittest.TestCase):

    def testGuessKnown(self):
        test_data = [ 
            ["Bruce Springsteen","The River"],
            ["The XX", "Intro"],
            ["Adele", "Tired"],
            ["Springsteen","Ghost of Tom Joad"]
            ]
        
        for [artist,title] in test_data:
            self.assertEqual(guess_order(artist, title), ORDER_ARTIST_TITLE)
            self.assertEqual(guess_order(title, artist), ORDER_TITLE_ARTIST)


    def testGuessUnknown(self):
        test_data = [ 
            ["unknown","unknown"],
            ["-", "-"],
            ["asdsdasda","kjhdfgs"]
            ]
        
        for [artist,title] in test_data:
            self.assertEqual(guess_order(artist, title), ORDER_UNKNOWN)
            self.assertEqual(guess_order(title, artist), ORDER_UNKNOWN)
            
    def testGuessStream(self):
        stream="test"
        artist = "Bruce Springsteen"
        title = "The River"
        
        self.assertEqual(guess_stream_order(stream,"unknown","unknown"), ORDER_UNKNOWN)
        for _i in range(0,8):
            self.assertEqual(guess_stream_order(stream,artist,title), ORDER_ARTIST_TITLE)
        self.assertEqual(guess_stream_order(stream,"unknown","unknown"), ORDER_ARTIST_TITLE)
        
        stream="test2"
        self.assertEqual(guess_stream_order(stream,"unknown","unknown"), ORDER_UNKNOWN)
        for _i in range(0,4):
            self.assertEqual(guess_stream_order(stream,artist,title), ORDER_ARTIST_TITLE)
            self.assertEqual(guess_stream_order(stream,title,artist), ORDER_TITLE_ARTIST)
        self.assertEqual(guess_stream_order(stream,"unknown","unknown"), ORDER_UNKNOWN)
        

if __name__ == "__main__":
    unittest.main()