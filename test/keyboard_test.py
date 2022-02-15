import py
from ac2.plugins.control.keyboard import Keyboard

def test_listener_started(caplog):
    keyboard = Keyboard()
    assert "keyboard listener started" in caplog.text
 