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

'''
This is the main audio control process that reads the configuration file,
initializes all subsystems and starts the required threads.

Functionality is implemented in the ac2.* modules
'''


import signal
import configparser
import logging
import os
import sys
from _collections import OrderedDict

from ac2.mpris import MPRISController
from ac2.metadata import lastfmuser
from ac2.lastfm import LastFMDisplay
from ac2.webserver import AudioControlWebserver
from ac2.alsavolume import ALSAVolume

import ac2.watchdog

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


def create_object(classname):
    #    [module_name, class_name] = classname.rsplit(".", 1)
    #    module = __import__(module_name)
    #    my_class = getattr(module, class_name)

    import importlib
    module_name, class_name = classname.rsplit(".", 1)
    MyClass = getattr(importlib.import_module(module_name), class_name)
    instance = MyClass()

    return instance


def parse_config(debugmode=False):
    server = None
    volume_control = None

    config = configparser.ConfigParser()
    config.optionxform = lambda option: option

#    config = configparser.RawConfigParser()
#    config.optionxform = lambda option: option

    config.read("/etc/audiocontrol2.conf")

    # Auto pause for mpris players
    auto_pause = False

    if "mpris" in config.sections():
        auto_pause = config.getboolean("mpris", "auto_pause",
                                       fallback=False)
        loop_delay = config.getint("mrpis", "loop_delay",
                                   fallback=1)
        mpris.loop_delay = loop_delay
        ignore_players = []
        for p in config.get("mpris", "ignore",
                            fallback="").split(","):
            playername = p.strip()
            ignore_players.append(playername)
            logging.info("Ignoring player %s", playername)

        mpris.ignore_players = ignore_players

    logging.debug("setting auto_pause for MPRIS players to %s",
                  auto_pause)
    mpris.auto_pause = auto_pause

    # Web server
    if config.getboolean("webserver", "enable", fallback=False):
        logging.debug("starting webserver")
        port = config.getint("webserver",
                             "port",
                             fallback=80)
        server = AudioControlWebserver(port=port, debug=debugmode)
        mpris.register_metadata_display(server)
        server.set_controller(mpris)
        logging.info("started web server on port %s", port)
    else:
        logging.error("web server disabled")

    # LastFMDisplay/LibreFM
    if "lastfm" in config.sections():
        network = config.get("lastfm", "network",
                             fallback="lastfm").lower()
        username = config.get("lastfm", "username",
                              fallback=None)
        password = config.get("lastfm", "password",
                              fallback=None)

        if network == "lastfm":
            apikey = "7d2431d8bb5608574b59ea9c7cfe5cbd"
            apisecret = "4722fea27727367810eb550759fa479f"
        elif network == "librefm":
            apikey = "hifiberry"
            apisecret = "hifiberryos"

        logging.info("Last.FM network %s", network)

        if network is not None:
            anon = False
            if username is None or \
                    password is None:
                logging.info("using %s anonymously", network)
                username = None
                password = None
                anon = True
            try:
                lastfmdisplay = LastFMDisplay(apikey,
                                              apisecret,
                                              username,
                                              password,
                                              None,
                                              network)
                lastfmdisplay.network.enable_caching()
                if not(anon):
                    mpris.register_metadata_display(lastfmdisplay)
                    logging.info("scrobbling to %s", network)
                    lastfmuser = username

                if server is not None:
                    server.set_lastfm_network(lastfmdisplay.network)

            except Exception as e:
                logging.error(e)

    else:
        logging.info("Last.FM not configured")

    # Watchdog
    if "watchdog" in config.sections():
        for player in config["watchdog"]:
            services = config["watchdog"][player].split(",")
            ac2.watchdog.player_mapping[player] = services
            logging.info("configuring watchdog %s: %s",
                         player, services)

    # Radio
    if server is not None and "radio" in config.sections():
        stations = OrderedDict()
        for station in config["radio"]:
            url = config["radio"][station]
            stations[station] = url
        server.set_radio_stations(stations)

    # Volume
    if "volume" in config.sections():
        mixer_name = config.get("volume",
                                "mixer_control",
                                fallback=None)
        if mixer_name is not None:
            volume_control = ALSAVolume(mixer_name)
            logging.info("monitoring mixer %s", mixer_name)

            if server is not None:
                volume_control.add_listener(server)
                server.volume_control = volume_control

            volume_control.start()

    # Keyboard volume control/remote control
    if "keyboard" in config.sections():
        logging.error("Keybor")
        from ac2.plugins.control.keyboard import Keyboard
        logging.error("Keybor2")
        keyboard_controller = Keyboard()
        logging.error("Keybor3")

        logging.info("starting keyboard listener")
        keyboard_controller.start()

    # Plugins
    if "plugins" in config.sections():
        plugin_dir = config.get("plugins",
                                "directory",
                                fallback=None)
        if plugin_dir is not None:
            sys.path.append(plugin_dir)

        for metadata_plugin in config.get("plugins",
                                          "metadata",
                                          fallback="").split(","):
            try:
                metadata_plugin = create_object(metadata_plugin)
                mpris.register_metadata_display(metadata_plugin)
                logging.info("Registered metadata plugin %s",
                             metadata_plugin)
            except Exception as e:
                logging.error("Can't load metadata plugin %s (%s)",
                              metadata_plugin,
                              e)

    if debugmode:
        from ac2.metadata import DummyMetadataCreator
        dummy = DummyMetadataCreator(server, interval=3)
        dummy.start()


def main():

    if len(sys.argv) > 1:
        if "-v" in sys.argv:
            logging.basicConfig(format='%(levelname)s: %(name)s - %(message)s',
                                level=logging.DEBUG)
            logging.debug("enabled verbose logging")
    else:
        logging.basicConfig(format='%(levelname)s: %(name)s - %(message)s',
                            level=logging.INFO)

    if ('DEBUG' in os.environ):
        logging.warning("Starting in debug mode...")
        debugmode = True
    else:
        debugmode = False

    parse_config(debugmode=debugmode)

    signal.signal(signal.SIGUSR1, pause_all)
    signal.signal(signal.SIGUSR2, print_state)

    # mpris.print_players()
    mpris.main_loop()


main()
