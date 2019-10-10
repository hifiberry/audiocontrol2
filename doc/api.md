# REST API

With the REST API you can control players using HTTP requests. At this point, no encryption and authentication are supported.

## Control player

Player control commands use POST requests
```
/ai/player/play
/api/player/pause
/api/player/playpause
/api/player/stop
/api/player/next
/api/player/previous
/api/player/love
/api/player/unlove
```

## Examples

```
curl -X post http://192.168.4.193:/api/player/previous
```
