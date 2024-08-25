#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    If terminated itself, it also terminates other processes/threads.
    (Motivation: to terminate an HTTP server that is not derived from LoopProcessor.)
'''

from time import sleep

# Root of project repository
from git_root_to_syspath import agr; PROJECT_ROOT = agr()

from src.processor import Processor
from src.loop_processor import LoopProcessor


class ProcessorTerminator(LoopProcessor):
    """
    Terminates a list of processors if the main processor is stopped.
    """

    def __init__(
        self,
        to_terminate: list[Processor] = [],
        sleep_time: float = 0.3,
        *args, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._to_terminate = to_terminate
        self._sleep_time = sleep_time

    def _work_in_loop(self):
        """
        Waits for the specified time in the loop.
        """
        sleep(self._sleep_time)

    def _set_stop_event_to_stop_and_log_it(self):
        """
        Terminate and join all processors in the to_terminate list.
        """
        for p in self._to_terminate:
            self.logger().info(f"Terminating {p}")
            p.terminate()
            p.join()
