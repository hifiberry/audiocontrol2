'''
Copyright (c) 2020 Modul 9/HiFiBerry

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''

import threading
import logging
import datetime
import time

control_registry={}
registered_players = None

class PlayerControl:

    def __init__(self, args):
        self.playername
        self.supported_commands=[]
        
        
    def start(self):
        # This might start a thread that handles updates
        pass
    
    def get_state(self):
        return {}
    
    def send_command(self,command, parameters={}):
        pass
    
    """
    Return a list of the commands that the player supports
    This can be dynamic based on the sate of the player
    """
    def get_supported_commands(self):
        return []
        
        
        
    """
    Checks if a player is active on the system and can result a 
    state. This does NOT mean this player is running
    """
    def is_active(self):
        return False
    
    
def add_control_registry(name,control_class):
    global control_registry, registered_players
    if name in control_registry:
        logging.error("PlayerControl %s already registered", name)
    else:
        control_registry[name]=control_class
        registered_players = None
        
        
def get_registered_players():
    global registered_players
    
    if registered_players is None:
        registered_players={}
        for name in control_registry:
            registered_players[name]=control_registry[name]()
            
    return registered_players
    
        
    
