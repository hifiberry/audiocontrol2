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

import logging
import os
import time
import signal

player_mapping = {}
monitored_threads = {}


def restart_service(service_name):
    if service_name in player_mapping:
        for service in player_mapping[service_name]:
            cmd = 'systemctl restart {}'.format(service)
            os.system(cmd)
    else:
        logging.warning("don't know how to restart %s", service_name)


def add_monitored_thread(thread, name):
    monitored_threads[name] = thread


def monitor_threads_and_exit():
    all_alive = True
    while all_alive:
        time.sleep(5)
        for threadname in monitored_threads:
            thread = monitored_threads[threadname]
            if not(thread.is_alive()):
                logging.error("Monitored thread %s died, exiting...", threadname)
                all_alive = False

    os.kill(os.getpid(), signal.SIGINT)
