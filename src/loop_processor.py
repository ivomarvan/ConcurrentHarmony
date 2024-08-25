#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Interface for typical tasks involving running something in a loop.
    It is assumed that each loop operates in a separate process/thread.
    Stopping or switching between active and inactive states is controlled via multiprocessing.Event.
'''

import os
from time import sleep
import multiprocessing
import platform

# Root of project repository
from git_root_to_syspath import agr;

PROJECT_ROOT = agr()
from src.processor import Processor
from src.signals.std_signals import SignalsEnum


class LoopProcessor(Processor):
    """
    Interface for a 'subprocess' that processes data in a loop.
    Can be in an active state (working) or inactive state (waiting).
    """

    def __init__(
            self,
            name: str = None,
            stop_event: multiprocessing.Event = None,
            is_waiting_event: multiprocessing.Event = None,
            start_active: bool = True,
            *args,
            **kwargs
    ):
        super().__init__(name, stop_event, *args, **kwargs)
        self._start_active = start_active
        self._is_active = True
        self._is_waiting_event = is_waiting_event
        self._is_waiting_if_waiting_event_is_not_defined = not self._start_active

    def set_waiting_event(self, is_waiting_event: multiprocessing.Event):
        """
        Set the waiting event if it is not already set.
        Does not overwrite an existing non-null is_waiting_event.
        """
        if self._is_waiting_event is None:
            if isinstance(is_waiting_event, multiprocessing.synchronize.Event):
                self._is_waiting_event = is_waiting_event
            else:
                raise ValueError('is_waiting_event must be an instance of Event')

    def is_active(self) -> bool:
        return self._is_active

    def _work_in_loop(self):
        """
        Perform the main work activity in the loop.
        """
        pass

    def _wait_in_loop(self):
        """
        Perform the waiting activity in the loop.
        """
        sleep(0.01)

    def _new_activity_state(self) -> bool:
        """
        Determine if the processor should be active based on the waiting event.
        """
        if self._is_waiting_event is None:
            return not self._is_waiting_if_waiting_event_is_not_defined
        return not self._is_waiting_event.is_set()

    def change_activity_state(self):
        """
        Toggle the active/inactive state of the processor.
        """
        if self._is_waiting_event is not None:
            if self._is_waiting_event.is_set():
                self._is_waiting_event.clear()
            else:
                self._is_waiting_event.set()
        else:
            self._is_waiting_if_waiting_event_is_not_defined = not self._is_waiting_if_waiting_event_is_not_defined

    def _became_active(self):
        """
        Hook method called when the processor becomes active.
        """
        pass

    def _became_inactive(self):
        """
        Hook method called when the processor becomes inactive.
        """
        pass

    def _react_if_activity_changes(self, is_active: bool):
        """
        Handle changes in the activity state.
        """
        if is_active != self._is_active:
            self._is_active = is_active
            if is_active:
                self._became_active()
            else:
                self._became_inactive()

    def run(self):
        """
        Main execution loop of the processor.
        """
        try:
            self.logger().info(f'+ START ({self.__class__.__name__}, PID={os.getpid()})')
            self._init_logging()
            self._before_body()
            self._is_active = False
            if self._start_active:
                self._react_if_activity_changes(True)  # start in active state
            while not self._is_stopped():
                is_active = self._new_activity_state()
                self._react_if_activity_changes(is_active)
                if self._is_active:
                    try:
                        self._work_in_loop()
                    except Exception as e:
                        self.logger().error(f'Loop error: {e}, (PID={os.getpid()}, {self.__class__.__name__})')
                        self.logger().exception(e)
                else:
                    self._wait_in_loop()
        except Exception as e:
            self.logger().error(f'Run error: {e}, (PID={os.getpid()}, {self.__class__.__name__})')
            self.logger().exception(e)
        finally:
            try:
                self._set_stop_event_to_stop_and_log_it()
            except Exception:
                self.logger().info('Error in _set_stop_event_to_stop_and_log_it()', exc_info=True)
            self._after_body()
            self.logger().info(f'- STOP ({self.__class__.__name__}, PID={os.getpid()})')
            sleep(0.5)

    def register_signals(self):
        """
        Register signals for process control (activate/deactivate) on Linux systems.
        """
        super().register_signals()
        if platform.system() == "Linux":
            self._register_signal(SignalsEnum.ACTIVATE, self.activate)
            self._register_signal(SignalsEnum.DEACTIVATE, self.deactivate)

    def activate(self, signal_number, frame):
        """
        Activate the processor in response to a signal.
        """
        if not self._new_activity_state():
            self.change_activity_state()

    def deactivate(self, signal_number, frame):
        """
        Deactivate the processor in response to a signal.
        """
        if self._new_activity_state():
            self.change_activity_state()
