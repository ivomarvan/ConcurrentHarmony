#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Reads data from a multiprocessing.Queue and writes it to a file.
    Works in an infinite loop.
    If termination is requested (via self.global_attributes().stop_all),
    it waits for the queue to empty before stopping.
    The wait is controlled by the wait_after_life_for_a_message parameter, 
    which specifies the time to wait after the last message is sent.
    If there are still messages in the queue, it waits again.
    This continues until the queue is empty.
'''

import multiprocessing
import logging
import time

# Root of project repository
from git_root_to_syspath import agr; PROJECT_ROOT = agr()

from src.log.log_manager import LogManager
from src.loop_processor import LoopProcessor
from src.concurrency_types import ConcurrencyType


class LogQueueStreamProcessor(LoopProcessor):

    def __init__(
        self,
        queue: multiprocessing.Queue,
        filename: str,
        multitasking_type: ConcurrencyType = ConcurrencyType.PROCESSES,
        timeout: float = 0.005,
        wait_after_life_for_a_message: float = 0.1,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._filename = filename
        self._multitasking_type = multitasking_type
        self.__queue = queue
        self._timeout = timeout
        # Parameters for stopping
        self._near_to_stop = False
        self._really_stop = False
        self._sleep_after_s = wait_after_life_for_a_message
        self._last_msg_send_time = None
        self._logger_private = LogManager.get_stream_logger(
            filename=self._filename,
            name='queue->stream',
            multitasking_type=self._multitasking_type,
            use_formatter=True
        )

    def logger(self) -> logging.Logger:
        return self._logger_private

    def _work_in_loop(self):
        """
        Main loop activity: process log records from the queue.
        """
        try:
            # Wait for a log record, which could be None
            log_record = self.__queue.get(timeout=self._timeout, block=True)
            self._logger_private.handle(log_record)
            if self._near_to_stop:
                self._last_msg_send_time = time.monotonic()  # Time of the last sent message
        except multiprocessing.queues.Empty:
            # No log record in the queue
            if self._near_to_stop:
                # Duration since the last message was sent
                from_last_send_time = time.monotonic() - self._last_msg_send_time
                if from_last_send_time > self._sleep_after_s:
                    self._really_stop = True
        except Exception as e:
            self._logger_private.error(f'Error in _work_in_loop: {e}')
            self._logger_private.exception(e)

    def _is_stopped(self) -> bool:
        if super()._is_stopped():
            if not self._near_to_stop:
                # Enter "near to stop" state
                self._near_to_stop = True
                self._last_msg_send_time = time.monotonic()  # Initialize time of the last sent message
                self._logger_private.info(
                    f'The logging process is requested to stop, there are {self.__queue.qsize()} messages in the queue. '
                    f'Logging stops if no new message arrives before the queue is exhausted in {self._sleep_after_s} seconds.'
                )
        return self._really_stop

    def _after_body(self):
        self._logger_private.info('LogQueueStreamProcessor: STOPPED')
