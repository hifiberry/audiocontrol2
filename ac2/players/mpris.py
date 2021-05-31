'''
Copyright (c) 2020 Modul 9/HiFiBerry

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

import dbus
import logging
from ac2.metadata import Metadata

from ac2.constants import CMD_NEXT, CMD_PAUSE, CMD_PLAY, CMD_PLAYPAUSE, CMD_PREV, CMD_STOP
from ac2.helpers import array_to_string

mpris_commands = [CMD_NEXT, CMD_PREV,
                  CMD_PAUSE, CMD_PLAYPAUSE,
                  CMD_STOP, CMD_PLAY]


MPRIS_PREFIX = "org.mpris.MediaPlayer2."


class MPRIS():
    
    def __init__(self):
        self.bus=None
           
    def connect_dbus(self):
        self.bus = dbus.SystemBus()
        self.device_prop_interfaces = {}

    def dbus_get_device_prop_interface(self, name):
        proxy = self.bus.get_object(name, "/org/mpris/MediaPlayer2")
        device_prop = dbus.Interface(
            proxy, "org.freedesktop.DBus.Properties")
        return device_prop
    
    def retrieve_players(self):
        """
        Returns a list of all MPRIS enabled players that are active in
        the system
        """
        return [name for name in self.bus.list_names()
                if name.startswith("org.mpris")]
        
        
    def retrieve_state(self, name):
    # This must be an MPRIS player
        try:
            device_prop = self.dbus_get_device_prop_interface(name)
            state = device_prop.Get("org.mpris.MediaPlayer2.Player",
                                    "PlaybackStatus")
            return state
        except Exception as e:
            logging.warn("got exception %s while polling MPRIS data", e)
            
            
    
    def get_supported_commands(self, name):
        commands = {
            "pause": "CanPause",
            "next": "CanGoNext",
            "previous": "CanGoPrevious",
            "play": "CanPlay",
            "seek": "CanSeek"
        }
        try:
            supported_commands = ["stop"]  # Stop must always be supported
            device_prop = self.dbus_get_device_prop_interface(name)
            for command in commands:
                supported = device_prop.Get("org.mpris.MediaPlayer2.Player",
                                            commands[command])
                if supported:
                    supported_commands.append(command)
        except Exception as e:
            logging.warn("got exception %s", e)

        return supported_commands
    
    
    
    def send_command(self, playername, command):
        
        if not playername.startswith(MPRIS_PREFIX):
            playername=MPRIS_PREFIX + playername
            
            
        try:
            if command in mpris_commands:
                proxy = self.bus.get_object(playername,
                                            "/org/mpris/MediaPlayer2")
                player = dbus.Interface(
                    proxy, dbus_interface='org.mpris.MediaPlayer2.Player')

                run_command = getattr(player, command,
                                      lambda: "Unknown command")
                return run_command()
            else:
                logging.error("MPRIS command %s not supported", command)
        except Exception as e:
            logging.error("exception %s while sending MPRIS command %s to %s",
                          e, command, playername)
            return False
        
    def playername(self, name):
        if name is None:
            return
        if (name.startswith(MPRIS_PREFIX)):
            return name[len(MPRIS_PREFIX):]
        else:
            return name
    
    
    def get_meta(self, name):
        """
        Return the metadata for the given player instance
        """
        try:
            device_prop = self.dbus_get_device_prop_interface(name)
            prop = device_prop.Get(
                "org.mpris.MediaPlayer2.Player", "Metadata")
            try:
                artist = array_to_string(prop.get("xesam:artist"))
            except:
                artist = None

            try:
                title = prop.get("xesam:title")
            except:
                title = None

            try:
                albumArtist = array_to_string(prop.get("xesam:albumArtist"))
            except:
                albumArtist = None

            try:
                albumTitle = prop.get("xesam:album")
            except:
                albumTitle = None

            try:
                artURL = prop.get("mpris:artUrl")
            except:
                artURL = None

            try:
                discNumber = prop.get("xesam:discNumber")
            except:
                discNumber = None

            try:
                trackNumber = prop.get("xesam:trackNumber")
            except:
                trackNumber = None

            md = Metadata(artist, title, albumArtist, albumTitle,
              artURL, discNumber, trackNumber)

            try:
                md.streamUrl = prop.get("xesam:url")
            except:
                pass

            try:
                md.trackId = prop.get("mpris:trackid")
            except:
                pass


            if (name.startswith(MPRIS_PREFIX)):
                md.playerName = name[len(MPRIS_PREFIX):]
            else:
                md.playerName = name

            return md

        except dbus.exceptions.DBusException as e:
            if "ServiceUnknown" in e.__class__.__name__:
                # unfortunately we can't do anything about this and
                # logging doesn't help, therefore just ignoring this case
                pass
                #  logging.warning("service %s disappered, cleaning up", e)
            else:
                logging.warning("no mpris data received %s", e.__class__.__name__)

            md = Metadata()
            md.playerName = self.playername(name)
            return md
