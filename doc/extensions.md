# Extending Audiocontrol

Adding more modules for audiocontrol is very simple.

## Metadata display

A metadata display receives updates when metadata change. This can be a new song, but also a change in the player 
state (e.g. from playing to paused)

```
class MyDisplay():

    def notify(self, metadata):
        # do something 
```

## Integrating extensions

Extensions can be integrated using the \[plugin\] section:

```[plugins]
plugin_dir=/data/ac2plugins
metadata=MyDisplay
```

plugin_dir defined a directory where modules are located.
metadata is a comma-seperated list of metadata display plugins
