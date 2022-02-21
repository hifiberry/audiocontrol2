import logging
from time import sleep

import pytest
from ac2.plugins.control.keyboard import Keyboard
from evdev import UInput, ecodes as e


@pytest.fixture
def test_keyboard():
    cap = {
        e.EV_KEY : [e.KEY_UP, e.KEY_DOWN, e.KEY_ENTER]
    }
    ui = UInput(cap, name='test_keyboard', version=0x3)
    yield ui

def test_listener_started(caplog, test_keyboard):
    caplog.set_level(logging.DEBUG)

    keyboard = Keyboard()
    keyboard.daemon = True
    keyboard.start()
    sleep(1)

    assert "keyboard listener started for test_keyboard" in caplog.text

def test_previous(caplog, test_keyboard):
    caplog.set_level(logging.DEBUG)

    keyboard = Keyboard()
    keyboard.daemon = True
    keyboard.start()
    sleep(1)

    assert "keyboard listener started for test_keyboard" in caplog.text

    test_keyboard.write(e.EV_KEY, e.KEY_UP, 1)
    test_keyboard.write(e.EV_KEY, e.KEY_UP, 0)
    test_keyboard.syn()

    sleep(1)
    assert "processed previous" in caplog.text
    assert "ignoring previous, no playback control" in caplog.text

def test_with_player_control(caplog, test_keyboard, mocker):
    caplog.set_level(logging.DEBUG)

    keyboard = Keyboard()
    player_control = mocker.Mock()
    keyboard.set_player_control(player_control)
    keyboard.daemon = True
    keyboard.start()
    sleep(1)

    assert "keyboard listener started for test_keyboard" in caplog.text

    test_keyboard.write(e.EV_KEY, e.KEY_UP, 1)
    test_keyboard.write(e.EV_KEY, e.KEY_UP, 0)
    test_keyboard.syn()

    sleep(1)
    assert "processed previous" in caplog.text
    assert player_control.previous.called_once()
    assert "ignoring previous, no playback control" not in caplog.text
