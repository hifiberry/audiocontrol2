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

from usagecollector.client import report_activate

from ac2.controller import AudioController
import ac2.data.lastfm as lastfmdata

from ac2.plugins.metadata.lastfm import LastFMScrobbler
from ac2.webserver import AudioControlWebserver
from ac2.alsavolume import ALSAVolume
from ac2.metadata import Metadata
import ac2.metadata
from ac2.data.mpd import MpdMetadataProcessor
from ac2.players.mpdcontrol import MPDControl
from ac2.players.vollibrespot import VollibspotifyControl
from ac2.players.vollibrespot import MYNAME as SPOTIFYNAME


from ac2 import watchdog

mpris = AudioController()
startup_command = None


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


def create_object(classname, param = None):
    #    [module_name, class_name] = classname.rsplit(".", 1)
    #    module = __import__(module_name)
    #    my_class = getattr(module, class_name)

    import importlib
    module_name, class_name = classname.rsplit(".", 1)
    MyClass = getattr(importlib.import_module(module_name), class_name)
    
    if param is None:
        instance = MyClass()
    else:
        instance = MyClass(param)

    return instance


def parse_config(debugmode=False):
    server = None

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
        server.add_updater(mpris)
        server.start()
        watchdog.add_monitored_thread(server, "webserver")
        report_activate("audiocontrol_webserver")
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
            if username is None or username == "" or \
                    password is None or password == "":
                logging.info("using %s anonymously, not scrobbling", network)
                username = None
                password = None
                anon = True

            if not(anon):
                try:
                    lastfmscrobbler = LastFMScrobbler(apikey,
                                                  apisecret,
                                                  username,
                                                  password,
                                                  None,
                                                  network)

                    mpris.register_metadata_display(lastfmscrobbler)
                    logging.info("scrobbling to %s as %s", network, username)
                    lastfmdata.set_lastfmuser(username)

                    if server is not None:
                        server.add_lover(lastfmscrobbler)
                        Metadata.loveSupportedDefault = True
                        
                    report_activate("audiocontrol_lastfm_scrobble")

                except Exception as e:
                    logging.error("error setting up lastfm module: %s", e)

    else:
        logging.info("Last.FM not configured")

    # Watchdog
    if "watchdog" in config.sections():
        for player in config["watchdog"]:
            services = config["watchdog"][player].split(",")
            watchdog.player_mapping[player] = services
            logging.info("configuring watchdog %s: %s",
                         player, services)

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

        mpris.set_volume_control(volume_control)
        
        report_activate("audiocontrol_volume")

    if volume_control is None:
        logging.info("volume control not configured, "
                     "disabling volume control support")

           
    # Additional controller modules
    for section in config.sections():
        if section.startswith("controller:"):
            [_,classname] = section.split(":",1)
            try:
                params = config[section]
                controller = create_object(classname, params)
                controller.set_player_control(mpris)
                controller.set_volume_control(volume_control)
                controller.start()
                logging.info("started controller %s", controller)
                report_activate("audiocontrol_controller_"+classname)
            except Exception as e:
                logging.error("Exception during controller %s initialization",
                              classname)
                logging.exception(e)

        if section.startswith("metadata:"):
            [_,classname] = section.split(":",1)
            try:
                params = config[section]
                metadata_display = create_object(classname, params)
                mpris.register_metadata_display(metadata_display)
                volume_control.add_listener(metadata_display)
                logging.info("registered metadata display %s", controller)
                report_activate("audiocontrol_metadata_"+classname)
            except Exception as e:
                logging.error("Exception during controller %s initialization",
                              classname)
                logging.exception(e)

    # Metadata push to GUI
    if "metadata_post" in config.sections():
        try:
            from ac2.plugins.metadata.http_post import MetadataHTTPRequest
            url = config.get("metadata_post",
                             "url",
                             fallback=None)

            if url is None:
                logging.error("can't activate metadata_post, url missing")
            else:
                logging.info("posting metadata to %s", url)

            metadata_pusher = MetadataHTTPRequest(url)
            mpris.register_metadata_display(metadata_pusher)

        except Exception as e:
            logging.error("can't activate metadata_post: %s", e)

    # Metadata push to GUI
    if "volume_post" in config.sections():
        if volume_control is None:
            logging.info("volume control not configured, "
                         "can't use volume_post")

        try:
            from ac2.plugins.volume.http import VolumeHTTPRequest
            url = config.get("volume_post",
                             "url",
                             fallback=None)

            if url is None:
                logging.error("can't activate volume_post, url missing")
            else:
                logging.info("posting volume changes to %s", url)

            volume_pusher = VolumeHTTPRequest(url)
            volume_control.add_listener(volume_pusher)

        except Exception as e:
            logging.error("can't activate volume_post: %s", e)
            
    # Native MPD backend and metadata processor
    if "mpd" in config.sections():
        mpdc = MPDControl()
        mpdc.start()
        mpris.register_nonmpris_player("mpd",mpdc)
        logging.info("registered non-MPRIS mpd backend")

        mpddir=config.get("mpd", "musicdir",fallback=None)
        if mpddir is not None:
            mpdproc = MpdMetadataProcessor(mpddir)
            mpris.register_metadata_processor(mpdproc)
            logging.info("added MPD cover art handler on %s",mpddir)
            
    # Vollibrespot
    vlrctl = VollibspotifyControl()
    vlrctl.start()
    mpris.register_nonmpris_player(SPOTIFYNAME,vlrctl)
            
            
    # Other settings
    if "privacy" in config.sections():
        extmd = config.getboolean("privacy",
                                  "external_metadata",
                                  fallback=True)
        if extmd:
            logging.info("external metadata enabled")
            ac2.metadata.external_metadata = True
        else:
            logging.info("external metadata disabled")
            ac2.metadata.external_metadata = False
    else:
        logging.info("no privacy settings found, using defaults")

    logging.debug("ac2.md.extmd %s", ac2.metadata.external_metadata)
    
    # Web server has to rewrite artwork URLs
    if server is not None:
        mpris.register_metadata_processor(server)
        logging.info("enabled web server meta data processor")
    

    # Other system settings
    global startup_command
    startup_command = config.get("system", "startup-finished", fallback=None)

    if debugmode:
        from ac2.dev.dummydata import DummyMetadataCreator
        dummy = DummyMetadataCreator(server, interval=3)
        dummy.start()


def main():

    if len(sys.argv) > 1:
        if "-v" in sys.argv:
            logging.basicConfig(format='%(levelname)s: %(module)s - %(message)s',
                                level=logging.DEBUG)
            logging.debug("enabled verbose logging")
    else:
        logging.basicConfig(format='%(levelname)s: %(module)s - %(message)s',
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

    logging.info("startup finished")
    if startup_command is not None:
        os.system(startup_command)

    # mpris.print_players()
    try:
        mpris.main_loop()
    except Exception as e:
        logging.error("main loop crashed with exception %s", e)
        logging.exception(e)

    logging.info("Main thread stopped")


main()
