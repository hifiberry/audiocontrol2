'''
Copyright (c) 2018 Modul 9/HiFiBerry

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

from time import sleep
from threading import Thread
from ac2.metadata import Metadata


class DummyMetadataCreator(Thread):
    """
    A class just use for development. It creates dummy metadata records and
    send it to the given MetadataDisplay objects
    """

    def __init__(self, display=None, interval=10):
        super().__init__()
        self.stop = False
        self.interval = interval
        self.display = display

    def run(self):
        import random

        covers = ["https://images-na.ssl-images-amazon.com/images/I/81R6Jcf5eoL._SL1500_.jpg",
                  "https://townsquare.media/site/443/files/2013/03/92rage.jpg?w=980&q=75",
                  "file://unknown.png",
                  None,
                  None,
                  None,
                  None
                  ]
        songs = [
            ["Madonna", "Like a Virgin"],
            ["Rammstein", "Mutter"],
            ["Iggy Pop", "James Bond"],
            ["Porcupine Tree", "Normal"],
            ["Clinton Shorter", "Truth"],
            ["Bruce Springsteen", "The River"],
            ["Plan B", "Kidz"],
            ["The Spooks", "Things I've seen"],
            ["Aldous Harding", "The Barrel"]
        ]

        states = ["playing", "paused", "stopped"]

        while not(self.stop):

            coverindex = random.randrange(len(covers))
            songindex = random.randrange(len(songs))
            stateindex = random.randrange(len(states))

            md = Metadata(artist=songs[songindex][0],
                          title=songs[songindex][1],
                          artUrl=covers[coverindex],
                          playerName="dummy",
                          playerState=states[stateindex])
            if self.display is not None:
                self.display.notify(md)

            sleep(self.interval)

    def stop(self):
        self.stop = True
