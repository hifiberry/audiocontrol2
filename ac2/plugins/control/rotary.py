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

import logging
from typing import Dict

from usagecollector.client import report_usage

from ac2.plugins.control.controller import Controller

from pyky040 import pyky040

class Rotary(Controller):

    def __init__(self, params: Dict[str, str]=None):
        super().__init__()
        
        self.clk = 4
        self.dt = 17
        self.sw = 27
        self.step = 5
        
        self.name = "rotary"
        
        if params is None:
            params={}
        
        if "clk" in params:
            try:
                self.clk = int(params["clk"])
            except:
                logging.error("can't parse %s",params["clk"])
            

        if "dt" in params:
            try:
                self.dt = int(params["dt"])
            except:
                logging.error("can't parse %s",params["dt"])

        if "sw" in params:
            try:
                self.sw = int(params["sw"])
            except:
                logging.error("can't parse %s",params["sw"])
                
        if "step" in params:
            try:
                self.step = int(params["step"])
            except:
                logging.error("can't parse %s",params["step"])
                
        logging.info("initializing rotary controller on GPIOs "
                     " clk=%s, dt=%s, sw=%s, step=%s%%",
                     self.clk, self.dt, self.sw, self.step)

        self.encoder = pyky040.Encoder(CLK=self.clk, DT=self.dt, SW=self.sw)
        self.encoder.setup(scale_min=0, 
                           scale_max=100, 
                           step=1, 
                           inc_callback=self.increase, 
                           dec_callback=self.decrease, 
                           sw_callback=self.button)
            
    def increase(self,val):
        if self.volumecontrol is not None:
            self.volumecontrol.change_volume_percent(self.step)
            report_usage("audiocontrol_rotary_volume", 1)
        else:
            logging.info("no volume control, ignoring rotary control")

    def decrease(self,val):
        if self.volumecontrol is not None:
            self.volumecontrol.change_volume_percent(-self.step)
            report_usage("audiocontrol_rotary_volume", 1)
        else:
            logging.info("no volume control, ignoring rotary control")

    def button(self):
        if self.playercontrol is not None:
            self.playercontrol.playpause()
            report_usage("audiocontrol_rotary_button", 1)
        else:
            logging.info("no player control, ignoring press")
    
    def run(self):
        self.encoder.watch()
