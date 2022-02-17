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

import asyncio
import logging

from typing import Dict
from usagecollector.client import report_usage

from ac2.plugins.control.controller import Controller
from evdev import InputDevice, ecodes, list_devices

class Keyboard(Controller):

    def __init__(self, params: Dict[str, str]=None):
        super().__init__()
        
        self.name = "keyboard"

        if params is None or len(params) == 0:
            # Default code table that works with this remote control:
            #
            self.codetable = {
                # volume up
                115: "volume_up",
                 # volume down
                114: "volume_down",
                # right
                106: "next",
                # left
                105: "previous",
                # enter
                28: "playpause",
                # up
                103: "previous",
                # down
                108: "next"
            }
        else:
            self.codetable = {}
            for i in params:
                self.codetable[int(params[i])] = i

    def handle_key_event(self, event):
        command = self.codetable.get(event.code)
        try:
            command_run = False
            if command == "volume_up":
                if self.volumecontrol is not None:
                    self.volumecontrol.change_volume_percent(5)
                    command_run =True
                else:
                    logging.info("ignoring %s, no volume control",
                                    command)

            elif command == "volume_down":
                if self.volumecontrol is not None:
                    self.volumecontrol.change_volume_percent(-5)
                    command_run =True
                else:
                    logging.info("ignoring %s, no volume control",
                                    command)

            elif command == "previous":
                if self.playercontrol is not None:
                    self.playercontrol.previous()
                    command_run =True
                else:
                    logging.info("ignoring %s, no playback control",
                                    command)

            elif command == "next":
                if self.playercontrol is not None:
                    self.playercontrol.next()
                    command_run =True
                else:
                    logging.info("ignoring %s, no playback control",
                                    command)

            elif command == "playpause":
                if self.playercontrol is not None:
                    self.playercontrol.playpause()


                    command_run =True
                else:
                    logging.info("ignoring %s, no playback control",
                                    command)

            if command_run:
                report_usage("audiocontrol_keyboard_key", 1)

            logging.debug("processed %s", command)

        except Exception as e:
            logging.warning("problem handling %s (%s)", command, e)

    def run(self):
        try:
            asyncio.run(self.bind_devices())
        except:
            logging.error("could not start Keyboard listener, "
                           "no keyboard detected or no permissions")

    async def bind_devices(self):
        await asyncio.gather(*[self.listen(keyboard) for keyboard in self.get_keyboards()])

    async def listen(self, dev):
        logging.info(f"keyboard listener started for {dev.name}")
        async for event in dev.async_read_loop():
            if event.type == ecodes.EV_KEY and event.value == 1:
                self.handle_key_event(event)

    def get_keyboards(self):
        devices = [InputDevice(path) for path in list_devices()]
        for device in devices:
            if 1 in device.capabilities():
                if any(x in self.codetable.keys() for x in device.capabilities()[1]):
                    yield device
