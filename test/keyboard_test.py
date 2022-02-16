import logging
from ac2.plugins.control.keyboard import Keyboard
from evdev import UInput, ecodes as e

def test_listener_started(caplog):
    caplog.set_level(logging.DEBUG)
    keyboard = Keyboard()
    assert "keyboard listener started" in caplog.text
