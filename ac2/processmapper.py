'''
Copyright (c) 2018 Modul 9/HiFiBerry

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

import logging


class ProcessMapper:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.name_to_process = {}
            cls._instance.process_to_name = {}
        return cls._instance

    def add_mapping(self, name, process_name):
        """
        Add a mapping between a name and a process name.
        """
        self.name_to_process[name] = process_name
        self.process_to_name[process_name] = name

    def get_process_name(self, name, defaultname=None):
        """
        Get the process name corresponding to a given name.
        """
        return self.name_to_process.get(name, defaultname)

    def get_name(self, process_name):
        """
        Get the name corresponding to a given process name.
        """
        return self.process_to_name.get(process_name)

    def load_mappings_from_config(self, config_section):
        """
        Load mappings from a section section of a config file.
        """
        for name, process_name in config_section.items():
            self.add_mapping(name, process_name)
            logging.debug("Added process mapping: %s -> %s", name, process_name)

