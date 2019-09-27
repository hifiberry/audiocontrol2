# Extending Audiocontrol 2

Adding more modules for audiocontrol is relatively simple.

## Metadata display

A metadata display receives updates when metadata change.

'''
class MyDisplay():

    def notify(self, metadata):
        # do something 
'''
