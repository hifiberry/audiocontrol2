import requests
import logging
from xml.etree import ElementTree

from ac2.players import PlayerControl
from ac2.constants import CMD_NEXT, CMD_PREV, CMD_PAUSE, CMD_PLAY, CMD_STOP, STATE_PAUSED
from ac2.metadata import Metadata

PLEXAMP_CMD_MAP={
    CMD_NEXT: "skipNext",
    CMD_PREV: "skipPrevious",
    CMD_PAUSE: "pause",
    CMD_PLAY: "play",
    CMD_STOP: "stop"
}

class PlexampControl(PlayerControl):
    def __init__(self, args={}):
        self.playername = "plexamp"
        self.state = STATE_PAUSED
        self.port = "32500"
        self.host = "127.0.0.1"

    def start(self):
        # No threading implemented
        pass

    def get_supported_commands(self):
        return [CMD_NEXT, CMD_PREV, CMD_PAUSE, CMD_PLAY, CMD_STOP]

    def get_timeline(self):
        response = requests.get("http://" + self.host + ":" + self.port + "/player/timeline/poll?wait=1&includeMetadata=1&commandID=1")
        return ElementTree.fromstring(response.content)

    def get_state(self):
        try:
           tree = self.get_timeline()
           timeline = tree.find("Timeline")
           return timeline.get("state")
        except Exception as e:
           return "stopped"

    def get_meta(self):
        try:
           metadata = Metadata()
           tree = self.get_timeline()
           timeline = tree.find("Timeline")
           track = tree.find('Timeline').find("Track")

           metadata.playerName = self.playername
           metadata.duration = timeline.get("duration")
           metadata.time = timeline.get("time")
           metadata.albumTitle = track.get("parentTitle")
           metadata.artist = track.get("grandparentTitle")
           metadata.title = track.get("title")
           metadata.releaseDate = track.get("parentYear")
           metadata.position = timeline.get("time")
           metadata.artUrl = timeline.get("protocol") + "://" + timeline.get("address") +  ":" + timeline.get("port") + "/photo/:/transcode?width=512&height=512&url=" + track.get("thumb")

           return metadata
        except Exception as e:
           metadata = Metadata()
           metadata.playerName = self.playername
           return metadata

    def send_command(self,command, parameters={}, mapping=True):
        if mapping and command not in self.get_supported_commands():
            return False

        if mapping:
            cmd = PLEXAMP_CMD_MAP[command]
        else:
            cmd = command

        requests.get("http://" + self.host + ":" + self.port + "/player/playback/" + cmd + "?commandID=1&type=music")

    def is_active(self):
        return True
