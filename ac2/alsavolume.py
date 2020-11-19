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
import alsaaudio

class ALSAVolume(threading.Thread):

    def __init__(self, mixer_name):

        super().__init__()

        self.listeners = []
        self.volume = -1
        self.unmuted_volume = 0
        self.pollinterval = 0.2
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
        # Check if this was a "mute" operation and store unmuted volume
        if vol == 0 and self.volume != 0:
            self.unmuted_volume = self.volume

        if vol != self.volume:
            alsaaudio.Mixer(self.mixer_name).setvolume(int(vol),
                                                       alsaaudio.MIXER_CHANNEL_ALL)

    def change_volume_percent(self, change):
        vol = self.current_volume()
        newvol = vol + change
        if newvol < 0:
            newvol = 0
        elif newvol > 100:
            newvol = 100

        self.set_volume(newvol)

    def set_mute(self, mute):
        if mute:
            logging.debug("muting")
            if self.volume != 0:
                self.unmuted_volume = self.volume
                self.set_volume(0)
        else:
            logging.debug("unmuting")
            if self.unmuted_volume > 0:
                self.set_volume(self.unmuted_volume)

    def run(self):
        while True:
            self.update_volume()
            time.sleep(self.pollinterval)

    def update_volume(self, always_notify=False):
        vol = self.current_volume()

        # Check if this was a "mute" operation and store unmuted volume
        if vol == 0 and self.volume != 0:
            self.unmuted_volume = self.volume

        if always_notify or (vol != self.volume):
            logging.debug("ALSA volume changed to {}".format(vol))
            self.volume = vol
            for listener in self.listeners:
                try:
                    listener.update_volume(vol)
                except Exception as e:
                    logging.debug("exception %s during %s.volume_changed_percent",
                                  e, listener)

    def current_volume(self):
        volumes = alsaaudio.Mixer(self.mixer_name).getvolume()
        channels = 0
        vol = 0
        for i in range(len(volumes)):
            channels += 1
            vol += volumes[i]

        if channels > 0:
            vol = vol / channels

        return vol

    def add_listener(self, listener):
        self.listeners.append(listener)
