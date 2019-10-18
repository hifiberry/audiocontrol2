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
import threading
from _collections import OrderedDict

from ac2.mpris import MPRISController
from ac2.metadata import lastfmuser
from ac2.lastfm import LastFMScrobbler
from ac2.webserver import AudioControlWebserver
from ac2.alsavolume import ALSAVolume

from ac2 import watchdog

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

    config.read("/etc/audiocontrol2.conf")

    # Auto pause for mpris players
    auto_pause = False

    if "mpris" in config.sections():
        auto_pause = config.getboolean("mpris", "auto_pause",
                                       fallback=False)
        loop_delay = config.getint("mpris", "loop_delay",
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
        server.set_player_control(mpris)
        server.start()
        watchdog.add_monitored_thread(server, "webserver")
        logging.info("started web server on port %s", port)
    else:
        logging.error("web server disabled")

    # LastFMScrobbler/LibreFM
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
                lastfmdisplay = LastFMScrobbler(apikey,
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
            watchdog.player_mapping[player] = services
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
    volume_control = None
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
            watchdog.add_monitored_thread(volume_control, "volume control")

    if volume_control is None:
        logging.info("volume control not configured, "
                     "disabling volume control support")

    # Keyboard volume control/remote control
    if "keyboard" in config.sections():
        moduleok = False
        try:
            from ac2.plugins.control.keyboard import Keyboard
            moduleok = True
        except Exception as e:
            logging.error("can't activate keyboard: %s", e)

        if moduleok:
            keyboard_controller = Keyboard()
            keyboard_controller.set_player_control(mpris)
            keyboard_controller.set_volume_control(volume_control)

            keyboard_controller.start()
            watchdog.add_monitored_thread(keyboard_controller,
                                          "keyboard controller")

            logging.info("started keyboard listener")

    # Metadata push to GUI
    if "metadata_post" in config.sections():
        moduleok = False
        try:
            from ac2.plugins.metadata.http import MetadataHTTPRequest
            moduleok = True
        except Exception as e:
            logging.error("can't activate metadata_post: %s", e)

        if moduleok:
            url = config.get("metadata_post",
                             "url",
                             fallback=None)

            if url is None:
                logging.error("can't activate metadata_post, url missing")
            else:
                logging.info("posting metadata to %s", url)

            metadata_pusher = MetadataHTTPRequest(url)
            mpris.register_metadata_display(metadata_pusher)

    # Metadata push to GUI
    if "volume_post" in config.sections():
        moduleok = False
        try:
            from ac2.plugins.volume.http import VolumeHTTPRequest
            moduleok = True
        except Exception as e:
            logging.error("can't activate volume_post: %s", e)

        if volume_control is None:
            logging.info("volume control not configured, "
                         "can't use volume_post")
            moduleok = False

        if moduleok:
            url = config.get("volume_post",
                             "url",
                             fallback=None)

            if url is None:
                logging.error("can't activate volume_post, url missing")
            else:
                logging.info("posting volume changes to %s", url)

            volume_pusher = VolumeHTTPRequest(url)
            volume_control.add_listener(volume_pusher)

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
                logging.info("registered metadata plugin %s",
                             metadata_plugin)
            except Exception as e:
                logging.error("can't load metadata plugin %s (%s)",
                              metadata_plugin,
                              e)

    if debugmode:
        from ac2.dev.dummydata import DummyMetadataCreator
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
        logging.warning("starting in debug mode...")
        debugmode = True
    else:
        debugmode = False

    parse_config(debugmode=debugmode)

    monitor = threading.Thread(target=watchdog.monitor_threads_and_exit)
    monitor.start()
    logging.info("started thread monitor for %s",
                 ",".join(watchdog.monitored_threads.keys()))

    signal.signal(signal.SIGUSR1, pause_all)
    signal.signal(signal.SIGUSR2, print_state)

    # mpris.print_players()
    mpris.main_loop()

    logging.info("Main thread stopped")


main()
