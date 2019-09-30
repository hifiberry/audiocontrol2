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

import threading
import time
import logging


class ALSAVolume(threading.Thread):

    def __init__(self, mixer_name):
        import alsaaudio

        super().__init__()

        self.listeners = []
        self.volume = -1
        self.pollinterval = 0.3
        if self.pollinterval < 0.1:
            self.pollinterval = 0.1

        try:
            alsaaudio.Mixer(mixer_name)
            self.mixer_name = mixer_name
        except:
            logging.error("ALSA mixer device %s not found, aborting",
                          mixer_name)
            self.mixer_name = None

    def set_volume(self, vol):
        import alsaaudio

        if vol != self.volume:
            alsaaudio.Mixer(self.mixer_name).setvolume(int(vol),
                                                       alsaaudio.MIXER_CHANNEL_ALL)

    def run(self):
        while True:
            self.update_volume()
            time.sleep(self.pollinterval)

    def update_volume(self, always_notify=False):
        import alsaaudio

        volumes = alsaaudio.Mixer(self.mixer_name).getvolume()
        channels = 0
        vol = 0
        for i in range(len(volumes)):
            channels += 1
            vol += volumes[i]

        if channels > 0:
            vol = vol / channels

        if always_notify or (vol != self.volume):
            logging.debug("ALSA volume changed to {}".format(vol))
            self.volume = vol
            for listener in self.listeners:
                try:
                    listener.update_volume(vol)
                except Exception as e:
                    logging.debug("exception %s during %s.volume_changed_percent",
                                  e, listener)

    def add_listener(self, listener):
        self.listeners.append(listener)
