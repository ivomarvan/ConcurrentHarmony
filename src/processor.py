#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Interface for typical tasks involving running something usually in a separate process/thread.
    Communicates via multiprocessing.Event .
'''

import multiprocessing
from multiprocessing import current_process, Event
from threading import current_thread
import signal
from time import sleep

# Root of project repository
from git_root_to_syspath import agr; PROJECT_ROOT = agr()

from src.run.rpi.signals import SignalsEnum
from src.log.log_manager import LoggerAccess
from src.concurrency_types import ConcurrencyType


class Processor(LoggerAccess):
    """
    Interface for a 'subprocess' which can be stopped and/or can stop other processes
    (by setting the flag 'stop_all').
    """

    def __init__(self, name: str = None, stop_event: Event = None):
        if name is None:
            name = self.__class__.__name__
        self._name = name
        self._multitasking_type = ConcurrencyType.THREADS  # default
        self._stop_event = stop_event
        self._stop_me_if_event_is_not_defined = False
        self.register_signals()

    def _rename_process_thread(self):
        """
        Rename the current process or thread based on the multitasking type.
        """
        if self._multitasking_type == ConcurrencyType.THREADS:
            thread = current_thread()
            if self._name is not None:
                thread.name = f't-{self._name}'
        elif self._multitasking_type == ConcurrencyType.PROCESSES:
            process = current_process()
            if self._name is not None:
                process.name = f'p-{self._name}'

    def set_multitasking_type(self, multitasking_type: ConcurrencyType):
        self._multitasking_type = multitasking_type

    def _init_logging(self):
        self._rename_process_thread()

    def _before_body(self):
        """
        Hook method to be overridden in subclasses, executed before the main body.
        """
        pass

    def _after_body(self):
        """
        Hook method to be overridden in subclasses, executed after the main body.
        """
        pass

    def _run_body(self):
        """
        Main method to be overridden in subclasses, containing the core logic.
        """
        pass

    def set_stop_event(self, stop_event: Event) -> bool:
        """
        Set the stop_event if it is not already set.
        Does not overwrite an existing non-null _stop_event.
        """
        if self._stop_event is None:
            if isinstance(stop_event, multiprocessing.synchronize.Event):
                self._stop_event = stop_event
                return True
            else:
                raise ValueError('stop_event must be an instance of Event')
        return False

    def _is_stopped(self) -> bool:
        """
        Determine if the process should stop based on the stop_event flags.
        """
        if self._stop_event is None:
            return self._stop_me_if_event_is_not_defined
        return self._stop_event.is_set()

    def _set_stop_event_to_stop_and_log_it(self):
        """
        Set the stop_event and log the stop attempt.
        """
        self.logger().info(self.__class__.__name__ + ' attempting to stop other processes')
        self.set_stop_event_to_stop()

    def set_stop_event_to_stop(self):
        """
        Set the stop_event, indicating that the process should stop.
        """
        if self._stop_event is not None:
            self._stop_event.set()
        else:
            self._stop_me_if_event_is_not_defined = True

    def stop(self):
        """
        Convenience method for stopping the process.
        """
        self.set_stop_event_to_stop()

    def run(self):
        """
        Execute the process, handling setup, main execution, and cleanup.
        """
        try:
            self._init_logging()
            self._before_body()
            self._run_body()
        finally:
            self._after_body()
            self.set_stop_event_to_stop()

    def register_signals(self):
        """
        Register signals for handling process termination.
        """
        self._register_signal(SignalsEnum.TERMINATE_ALL, self._terminate)

    @classmethod
    def _register_signal(cls, enum_signal, call_back):
        """
        Register a specific signal with its corresponding callback.
        """
        signal.signal(enum_signal.value, call_back)

    def _terminate(self, signal_number, frame):
        """
        Handle the termination signal, logging and setting the stop event.
        """
        self.logger().info(f'terminate({signal_number}, {frame})')
        self.set_stop_event_to_stop()
        self.logger().debug(f'{self.name()} stop_event is set: {self._stop_event.is_set()}')
        sleep(0.1)

    def name(self) -> str:
        """
        Return the name of the process or thread.
        """
        return self._name
