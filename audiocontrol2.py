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

import signal

import configparser
import logging
import os

from mpris import MPRISController
from metadata import MetadataConsole, DummyMetadataCreator
from lastfm import LastFM
from webserver import AudioControlWebserver

mpris = MPRISController()


def pause_all(signalNumber=None, frame=None):
    """
    Pause all players on SIGUSR1
    """
    if mpris is not None:
        mpris.pause_all()


def print_state(signalNumber=None, frame=None):
    """
    Display state on USR2
    """
    if mpris is not None:
        print("\n" + str(mpris))


def parse_config(debugmode=False):
    config = configparser.ConfigParser()
    config.read('/etc/audiocontrol2.conf')

    # Auto pause for mpris players
    auto_pause = config.getboolean('mpris', 'auto_pause',
                                   fallback=False)
    logging.debug("Setting auto_pause for MPRIS players to %s",
                  auto_pause)
    mpris.auto_pause = auto_pause

    # Console metadata logger
    if config.getboolean('metadata', 'logger-console', fallback=False):
        logging.debug("Starting console logger")
        mpris.register_metadata_display(MetadataConsole())

    # Web server
    if config.getboolean('webserver', 'webserver-enable', fallback=False):
        logging.debug("Starting webserver")
        port = config.getint('webserver',
                             'webserver-port',
                             fallback=80)
        server = AudioControlWebserver(port=port, debug=debugmode)
        mpris.register_metadata_display(server)
        server.set_controller(mpris)
    else:
        logging.error("Won't start web server")

    # LastFM/LibreFM
    try:
        scrobbler_network = config.get("scrobbler", "scrobbler-network",
                                       fallback="lastfm")
        scrobbler_apikey = config.get("scrobbler", "scrobbler-apikey")
        scrobbler_apisecret = config.get("scrobbler", "scrobbler-apisecret")
        scrobbler_username = config.get("scrobbler", "scrobbler-username")
        scrobbler_password = config.get("scrobbler", "scrobbler-password")

        if (scrobbler_apikey is not None) and \
            (scrobbler_apisecret is not None) and \
            (scrobbler_apisecret is not None) and \
                (scrobbler_password is not None):
            try:
                lastfm = LastFM(scrobbler_apikey,
                                scrobbler_apisecret,
                                scrobbler_username,
                                scrobbler_password,
                                None,
                                scrobbler_network)
                mpris.register_metadata_display(lastfm)
                logging.info("Scrobbling to %s", scrobbler_network)
            except Exception as e:
                logging.error(e)

    except Exception as e:
        logging.info("LastFM not configured, won't use it")

    if debugmode:
        dummy = DummyMetadataCreator(server, interval=3)
        dummy.start()


def main():

    if ('DEBUG' in os.environ):
        print("Starting in debug mode...")
        debugmode = True
    else:
        debugmode = False

    parse_config(debugmode=debugmode)

    signal.signal(signal.SIGUSR1, pause_all)
    signal.signal(signal.SIGUSR2, print_state)

    # mpris.print_players()
    mpris.main_loop()


main()
