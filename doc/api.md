# REST API

With the REST API you can control players using HTTP requests. At this point, no encryption and authentication are supported.

## Control player

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

Note that this is mostly for debugging, the format might change without further notice.

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
curl -X POST -H "Content-Type: application/json" -d '{"percent":"50"} http://127.0.0.1:/api/volume
```



## Examples

```
curl -X post http://127.0.0.1:/api/player/previous
curl -X post http://127.0.0.1:/api/track/love
curl http://127.0.0.1:/api/track/metadata
```
