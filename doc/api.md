# REST API

With the REST API you can control players using HTTP requests. At this point, no encryption and authentication are supported.

## Control active player

Player control commands use POST requests
```
/api/player/play
/api/player/pause
/api/player/playpause
/api/player/stop
/api/player/next
/api/player/previous
```

## Player status

List of all players with their current status can be retrieved by a GET to
```
/api/player/status
```

## Activate another player
```
/api/player/activate/<playername>
```

This will start music playback on the given player. Note that this will just send a
PLAY command to this specific player. Not all players might support this for various reasons:
- player is not enabled
- player is not connected to a server
- player has not active playlist
- player is already running on another server
- ...

If this player can't become active for any of these reasons, the current player will stay active.

## Metadata

Metadata of the current track can be retrieved by a GET to 
```
/api/track/metadata
```

## Love/unlove

To send a love/unlove to Last.FM (if configured), use a HTTP POST to

```
/api/track/love
/api/track/unlove
```

## Volume

```
/api/volume
```

This endpoint can be used to get the current volume using a HTTP get request
or set the volume using HTTP POST.

When setting the volume, use JSON encoding with the volume defined as "percent":

```
curl -X POST -H "Content-Type: application/json" -d '{"percent":"50"}' http://127.0.0.1:80/api/volume
```

If the percent value starts with + or -, it will change the volume by this amount (e.g. "+1" will by
[one louder](https://www.youtube.com/watch?v=_sRhuh8Aphc))

## System
```
/api/system/poweroff
```

This endpoint is used to turnoff your device in a controlled maner using an authenticated (header `Authtoken`) HTTP POST request.

This endpoint is only available if your `/etc/audiocontrol2.conf` includes a secret authorization token (`authtoken`):
```
[webserver]
enable=yes
port=81
authtoken=hifiberry
```

## Examples

Note that these examples assume audiocontrol to listen on port 80. On HiFiBerryOS, audiocontrol is listening on port 81. Therefore, you will need to change the port number.

```
curl -X post http://127.0.0.1:80/api/player/previous
curl -X post http://127.0.0.1:80/api/track/love
curl http://127.0.0.1:80/api/track/metadata
curl -X POST -H "Content-Type: application/json" -d '{"percent":"+5"} http://127.0.0.1:80/api/volume
curl -X POST hifiberry.local:81/api/system/poweroff -H "Authtoken: hifiberry"
```
