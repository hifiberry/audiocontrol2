'''
Copyright (c) 2021 Modul 9/HiFiBerry
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

import logging
import time
import os
from typing import Dict

from smbus import SMBus

from ac2.constants import STATE_PLAYING, STATE_UNDEF
from ac2.plugins.control.controller import Controller
from usagecollector.client import report_usage

ADDRESS = 0x77

REG_VL = 0xfd
REG_VH = 0xfe
REG_ROTARYCHANGE = 0x0c
REG_LEDMODE = 0x01
REG_LEDR = 0x02
REG_LEDG = 0x03
REG_LEDB = 0x04
REG_BUTTONMODE = 0x05
REG_BUTTONSTATE = 0x06
REG_POWEROFFTIMER = 0x09
REG_BUTTONPOWEROFFTIME = 0x0a
REG_INTERRUPTPIN = 0x0e

LEDMODE_STATIC = 0
LEDMODE_PULSING = 1
LEDMODE_BLINK = 2
LEDMODE_FLASH = 3
LEDMODE_OFF = 4

# Use Pi's GPIO15 (RXD) as interrupt pin
INTPINS = {
    0: 0,
    1: 4,
    2: 15,
    3: 14
    }

BUTTONMODE_SHORT_LONG_PRESS = 0

MIN_VERSION = 4  # requires functionality to set interrupt pin that was introduced in v4


def twos_comp(val, bits):
    """compute the 2's complement of int value val"""
    if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)  # compute negative value
    return val  # return positive value as is


class Powercontroller(Controller):
    """
    Support for the HiFiBerry power controller
    """

    def __init__(self, params: Dict[str, str]=None):
        super().__init__()

        self.name = "powercontroller"
        self.finished = False
        self.bus = SMBus(1)
        self.stepsize = 2
        self.intpin = 0
        self.intpinpi = 0

        # configure GPIO
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setup((4, 14, 15), GPIO.IN)
        except:
            logging.error("Couldn't import RPi.GPIO, won't load powercontroller module")
            self.finished = True
            return

        if params is None:
            params = {}

        try:
            self.intpin = int(params.get("intpin", "1"), base=10)
            if self.intpin == 0:
                self.intpin = 1

            self.intpinpi = INTPINS[self.intpin]
            logging.info("Using controller int pin %s on GPIO %s", self.intpin, self.intpinpi)
        except Exception as e:
            logging.error("can't read intpin, won't start powercontroller plugin (%s)", e)
            self.finished = True

        try:
            vl = self.bus.read_byte_data(ADDRESS, REG_VL)
            vh = self.bus.read_byte_data(ADDRESS, REG_VH)
            version = 256 * vh + vl
            logging.info("found powercontroller software version %s on I2C address %s", version, ADDRESS)
            if version < MIN_VERSION:
                logging.error("version %s is lower than minimal supported version %s, stopping",
                              version, MIN_VERSION)
                self.finished = True
            else:
                # TODO: report activation
                pass

            self.init_controller()

        except Exception as e:
            logging.error("no power controller found, ignoring, %s", e)
            self.finished = True

    def init_controller(self):
        self.bus.write_byte_data(ADDRESS, REG_BUTTONPOWEROFFTIME, 20)  # We deal with this directly
        self.bus.write_byte_data(ADDRESS, REG_BUTTONMODE, BUTTONMODE_SHORT_LONG_PRESS)
        self.bus.write_byte_data(ADDRESS, REG_INTERRUPTPIN, self.intpin)  # Set interrupt pin
        self.update_playback_state(STATE_UNDEF)

    def volchange(self, val):
        if self.volumecontrol is not None:
            self.volumecontrol.change_volume_percent(val)
            report_usage("audiocontrol_powercontroller_volume", 1)
        else:
            logging.info("no volume control, ignoring powercontroller feedback")

    def playpause(self):
        if self.playercontrol is not None:
            self.playercontrol.playpause()
            report_usage("audiocontrol_powercontroller_button", 1)
        else:
            logging.info("no player control, ignoring press")

    def update_playback_state(self, state):
        if self.playerstate != state:
            self.playerstate = state
            logging.info("Update LED state for state=%s", state)
            try:
                if state == STATE_PLAYING:
                    self.bus.write_byte_data(ADDRESS, REG_LEDR, 0)
                    self.bus.write_byte_data(ADDRESS, REG_LEDG, 100)
                    self.bus.write_byte_data(ADDRESS, REG_LEDB, 0)
                    self.bus.write_byte_data(ADDRESS, REG_LEDMODE, LEDMODE_STATIC)
                else:
                    self.bus.write_byte_data(ADDRESS, REG_LEDR, 0)
                    self.bus.write_byte_data(ADDRESS, REG_LEDG, 0)
                    self.bus.write_byte_data(ADDRESS, REG_LEDB, 80)
                    self.bus.write_byte_data(ADDRESS, REG_LEDMODE, LEDMODE_PULSING)
            except Exception as e:
                logging.error("Could not write to power controller: %s", e)

    def shutdown(self):
        logging.info("shutdown initiated by button press")
        self.bus.write_byte_data(ADDRESS, REG_LEDR, 100)
        self.bus.write_byte_data(ADDRESS, REG_LEDG, 0)
        self.bus.write_byte_data(ADDRESS, REG_LEDB, 0)
        self.bus.write_byte_data(ADDRESS, REG_LEDMODE, LEDMODE_BLINK)
        self.bus.write_byte_data(ADDRESS, REG_POWEROFFTIMER, 30)  # poweroff in 30 seconds

        os.system("systemctl poweroff")

    def interrupt_callback(self, channel):
        logging.info("Received interrupt")

        try:
            rotary_change = twos_comp(self.bus.read_byte_data(ADDRESS, REG_ROTARYCHANGE), 8)  # this is a signed byte
            button_state = self.bus.read_byte_data(ADDRESS, REG_BUTTONSTATE)

            if rotary_change != 0:
                self.volchange(rotary_change * self.stepsize)

            if button_state == 1:
                # short pressure_network
                self.bus.write_byte_data(ADDRESS, REG_BUTTONSTATE, 0)
                self.playpause()
            elif button_state == 2:
                # Long press
                self.bus.write_byte_data(ADDRESS, REG_BUTTONSTATE, 0)
                self.shutdown();

            logging.info("Received interrupt (rotary_change=%s, button_state=%s",
                         rotary_change, button_state)
        except Exception as e:
            logging.error("Couldn't read data form I2C, aborting... (%s)", e)
            self.finished = True

    def run(self):

        try:
            GPIO.add_event_detect(self.intpinpi, GPIO.BOTH, callback=self.interrupt_callback)
        except Exception as e:
            logging.error("Couldn't start GPIO callback, aborting... (%s)", e)
            self.finished = True
