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
import logging
import datetime
import time


class MetadataDisplay:

    def __init__(self):
        logging.debug("initializing MetadataDisplay instance")
        self.notifierthread = None
        self.starttime = None
        self.async_delay = 1
        pass

    def notify(self, metadata):
        raise RuntimeError("notify not implemented")

    def notify_async(self, metadata):
        # Don't run 2 async notifier threads in parallel
        # If there is already one running. wait a bit and try again
        if self.notifierthread is not None and self.notifierthread.is_alive():
            time.sleep(self.async_delay)
        
        if self.notifierthread is not None and self.notifierthread.is_alive():            
            logging.info("notifier background thread %s still running after %s seconds, "
                         "not sending notify",
                         self.notifierthread,
                         datetime.datetime.now() - self.notifystarttime)
        else:
            self.notifierthread = threading.Thread(target=self.notify,
                                                       args=(metadata,),
                                                       name="notifier thread "+self.__str__())
            self.notifystarttime = datetime.datetime.now()
            self.notifierthread.start()
