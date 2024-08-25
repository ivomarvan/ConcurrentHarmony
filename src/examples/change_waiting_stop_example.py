#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Runs all test fake processes to test the concept (no real peripherals/sensors).

    The first process simply terminates everything after some time.
    The second process runs two threads:
    - The first thread toggles its own activity and the activity of the second thread (with some delay in both active and inactive phases).
    - The second thread only logs its activity (with some delay in both active and inactive phases).

    - The event for stopping all processes (multiprocessing.Event) is shared among all processors.
      It is created implicitly in src.runner.ProcessorsRunner.
    - The event for changing activity is shared only between the two threads and must be explicitly created for this purpose.

    The output is logged to the file change_waiting_stop_example.py.log.txt.
'''

import logging
from time import sleep
import os
import multiprocessing

# Root of project repository
from git_root_to_syspath import agr;

PROJECT_ROOT = agr()

from src.loop_processor import LoopProcessor
from src.concurrency_types import ConcurrencyType
from src.processor import Processor
from src.runner import ProcessorsRunner
from src.log.log_manager import LogManager


class DbgProcessor(Processor):
    """
    A processor without a loop that logs its activity.
    """

    def __init__(self, name: str, *args, **kwargs):
        super().__init__(name=name, *args, **kwargs)
        self._msg_id = 0

    def log(self, msg: str):
        msg = f'{self._name}.{self._msg_id}: {msg}'
        self.logger().debug(msg)
        self._msg_id += 1

    def _before_body(self):
        self.log('_before_body')

    def _after_body(self):
        self.log('_after_body')

    def _run_body(self):
        self.log('_run_body')


class DbgLoopProcessor(LoopProcessor):
    """
    A processor with a loop that logs its activity.
    """

    def __init__(self, name: str, *args, **kwargs):
        super().__init__(name=name, *args, **kwargs)
        self._msg_id = 0

    def log(self, msg: str):
        msg = f'{self._name}.{self._msg_id}: {msg}'
        self.logger().debug(msg)
        self._msg_id += 1

    def _before_body(self):
        self.log('_before_body')

    def _after_body(self):
        self.log('_after_body')

    def _run_body(self):
        self.log('_run_body')

    def log_activity_with_params(self, in_work: bool, **kwargs):
        msg = 'WORK' if in_work else 'WAIT'
        for j, (key, value) in enumerate(kwargs.items()):
            if j == 0:
                msg += ', '
            msg += f'{key}: {value}'
        self.log(msg)

    def _work_in_loop(self):
        self.log_activity_with_params(in_work=True)

    def _wait_in_loop(self):
        self.log_activity_with_params(in_work=False)


class FakeProcessorMaxTime(DbgProcessor):
    """
    Terminates other processes after a given time. Does nothing else.
    """

    def __init__(self, max_seconds=2, *args, **kwargs):
        super().__init__(name='MaxTime', *args, **kwargs)
        self._max_seconds = max_seconds

    def _run_body(self):
        super()._run_body()
        self.log(f'wait for {self._max_seconds} seconds')
        sleep(self._max_seconds)
        self.log(f'trying to stop all processes')
        self._set_stop_event_to_stop_and_log_it()


class FakeProcessorChangeStateLoop(DbgLoopProcessor):
    """
    Continuously changes its activity state.
    If the same multiprocessing.Event is set for another process, it changes its state as well.
    """

    def __init__(self, max_count=20, sleep_s: int = 0.4, *args, **kwargs):
        super().__init__(name='ChangeState', *args, **kwargs)
        self._max_count = max_count
        self._sleep_s = sleep_s
        self._i = 0

    def _work_in_loop(self):
        self.log_activity_with_params(in_work=True, i=self._i)
        self._change_state()
