# Socketio API
With this API you can control players with socketio. It is possible the register for metadata and volume events.

# Howto enable Socketio API
This API is only available if it is enabled in your `etc/audiocontrol2.conf`:
```
[webserver]
enable=yes
port=81
socketio_enabled=True
```

# Example client
This client prints the metadata json dump whenever new metadata is available in audiocontrol2.
Use pip install "python-socketio[asyncio_client]" to install socketio with the async client. Be aware to use the same version of socketio as install on HiFiBerryOS (5.4.0 at the time of writing).

```
import asyncio
import json
import socketio

sio = socketio.AsyncClient()

@sio.event
async def connect():
    print('connection established')

@sio.event(namespace="/metadata")
async def update(data):
    print('metadata update: %s', json.dumps(data))

@sio.event
async def disconnect():
    print('disconnected from server')

async def main():
    await sio.connect('http://hifiberry.local:81')
    await sio.wait()

if __name__ == '__main__':
    asyncio.run(main())
```
