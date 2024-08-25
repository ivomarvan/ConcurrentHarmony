#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Types of parallel execution: process vs. thread (multiprocessing vs threads).
'''

from enum import Enum, auto


class ConcurrencyType(Enum):
    """
    Enum representing the types of concurrency: processes or threads.
    """
    PROCESSES = auto()
    THREADS = auto()


