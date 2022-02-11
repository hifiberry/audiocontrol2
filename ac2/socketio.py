import json
import logging

import socketio
from bottle import Bottle
from ac2.controller import AudioController
from ac2.metadata import Metadata

from ac2.plugins.metadata import MetadataDisplay

_LOGGER = logging.getLogger(__name__)
sio = socketio.Server()

@sio.event
def connect(sid, environ):
    _LOGGER.info("connect client %s", sid)

@sio.event
def disconnect(sid):
    _LOGGER.info("disconnect client %s", sid)


class MetadataHandler(socketio.Namespace, MetadataDisplay):

    def __init__(self):
        super().__init__(namespace='/metadata')
        MetadataDisplay.__init__(self)
        self.metadata = Metadata()

    def on_get(self, sid):
        _LOGGER.debug("metadata on_get event from %s", sid)
        return self.metadata.__dict__

    def notify(self, metadata):
        _LOGGER.debug('metadata notify: %s', json.dumps(self.metadata.__dict__, skipkeys=True))
        self.metadata = metadata
        sio.emit("update", self.metadata.__dict__, namespace="/metadata")


class PlayerHandler(socketio.Namespace):

    def __init__(self, audio_controller: AudioController):
        super().__init__(namespace='/player')
        self.audio_controller = audio_controller

    def on_status(self, sid):
        _LOGGER.debug("player status event from %s", sid)
        return self.audio_controller.states()
        
    def on_playing(self, sid):
        _LOGGER.debug("player playing event from %s", sid)
        return self.audio_controller.playing
        
    def on_play(self, sid):
        _LOGGER.debug("player play event from %s", sid)
        self.audio_controller.playpause(pause=False)

    def on_pause(self, sid):
        _LOGGER.debug("player pause event from %s", sid)
        self.audio_controller.playpause(pause=True)

    def on_play_pause(self, sid):
        _LOGGER.debug("player playpause event from %s", sid)
        self.audio_controller.playpause(pause=None)

    def on_stop(self, sid):
        _LOGGER.debug("player stop event from %s", sid)
        self.audio_controller.stop()

    def on_next(self, sid):
        _LOGGER.debug("player next event from %s", sid)
        self.audio_controller.next()

    def on_previous(self, sid):
        _LOGGER.debug("player previous event from %s", sid)
        self.audio_controller.previous()


class VolumeHandler(socketio.Namespace):

    def __init__(self, audio_controller: AudioController):
        super().__init__(namespace='/volume')
        self.audio_controller = audio_controller

    def notify_volume(self, volume):
        _LOGGER.debug('volume update %s', volume)
        self.volume = volume
        sio.emit("update", {'percent': volume}, namespace="/volume")

    def on_get(self, sid):
        _LOGGER.debug("volume get event from %s", sid)
        if not self.audio_controller.volume_control:
            return {"error": "no volume control available"}
        return {"percent": self.audio_controller.volume_control.current_volume()}

    def on_set(self, sid, volume):
        _LOGGER.debug("volume set event from %s", sid)
        if not self.audio_controller.volume_control:
            return {"error": "no volume control available"}
        try:
            self.audio_controller.volume_control.set_volume(volume['percent'])
        except:
            return {"error": "volume needs to be sent as json like {'percent': 50}"}
        return {"percent": self.audio_controller.volume_control.current_volume()}

class SocketioAPI():
    def __init__(self, bottle: Bottle, audio_controller: AudioController) -> None:
        self.app = socketio.WSGIApp(sio, bottle)
        self.player_handler = PlayerHandler(audio_controller)
        sio.register_namespace(self.player_handler)
        self.metadata_handler = MetadataHandler()
        sio.register_namespace(self.metadata_handler)
        self.volume_handler = VolumeHandler(audio_controller)
        sio.register_namespace(self.volume_handler)
