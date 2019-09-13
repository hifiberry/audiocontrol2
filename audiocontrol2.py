import signal

from mpris import MPRISController
from metadata import MetadataConsole, MetadataWebserver

mpris = MPRISController()


def pause_all(signalNumber=None, frame=None):
    """
    Pause all players on SIGUSR1
    """
    if mpris is not None:
        mpris.pause_all()


def print_state(signalNumber=None, frame=None):
    """
    Display state on USR2
    """
    if mpris is not None:
        print("\n" + str(mpris))


def main():

    mpris.register_metadata_display(MetadataConsole())
    ws = MetadataWebserver()
    ws.run_server()
    mpris.register_metadata_display(ws)

    signal.signal(signal.SIGUSR1, pause_all)
    signal.signal(signal.SIGUSR2, print_state)

    # mpris.print_players()
    mpris.main_loop()


main()
