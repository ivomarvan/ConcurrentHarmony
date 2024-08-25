#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Defines signals for activating, deactivating logging, and other operations.
'''

from enum import Enum
import signal
import platform

class SignalsEnum(Enum):
    # Define signals for Linux systems
    if platform.system() == "Linux":
        ACTIVATE = signal.SIGUSR1
        DEACTIVATE = signal.SIGUSR2
    # Signal for terminating all processes
    TERMINATE_ALL = signal.SIGTERM


if __name__ == '__main__':
    from pprint import pprint
    # Iterate over all valid signals and print their details
    for sig in signal.valid_signals():
        pprint(sig)
        print(f'sig:{sig}, type(sig):{type(sig)}, signal.strsignal(sig):{signal.strsignal(sig)}\n')



