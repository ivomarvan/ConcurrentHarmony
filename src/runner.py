#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Runs processors (workers) in separate threads and/or processes.
'''

import multiprocessing

# Root of project repository
from git_root_to_syspath import agr; PROJECT_ROOT = agr()
from src.concurrency_types import ConcurrencyType
from src.processor import Processor
from src.loop_processor import LoopProcessor
from src.log.log_queue_stream_processor import LogQueueStreamProcessor
from src.log.log_manager import LogManager


class ProcessorsRunner(Processor):
    """
    Run processors (workers), each in its own process/thread.
    It is a worker itself and can be nested within another runner.
    """

    def __init__(
            self,
            multitasking_type: ConcurrencyType,
            workers: [Processor],
            name: str = None,
            stop_event: multiprocessing.Event = None,
            is_waiting_event: multiprocessing.Event = multiprocessing.Event(),
            *args, **kwargs
    ):
        super().__init__(name=name, stop_event=stop_event, *args, **kwargs)
        self.multitasking_type = multitasking_type
        self._TaskClass = self._get_multitasking_class()
        self._workers = workers
        self._tasks = []
        self._is_waiting_event = is_waiting_event
        self.set_events_to_processors()

    def set_events_to_processors(self):
        """
        Set the stop and waiting events for all workers.
        """
        for worker in self._workers:
            if isinstance(worker, LoopProcessor) and self._is_waiting_event is not None:
                worker.set_waiting_event(self._is_waiting_event)
                self.logger().debug(
                    f'Waiting event: {hex(id(self._is_waiting_event))} '
                    f'(is_set:{self._is_waiting_event.is_set()}) to {worker.name()}'
                )
            if isinstance(worker, Processor) and self._stop_event is not None:
                self.logger().debug(
                    f'Stop event: {hex(id(self._stop_event))} '
                    f'(is_set:{self._stop_event.is_set()}) to {worker.name()}')
                worker.set_stop_event(self._stop_event)
            if isinstance(worker, ProcessorsRunner):
                # Set the events of all nested processors (recursively)
                # only after these events have already been set for this runner.
                worker.set_events_to_processors()

    def _get_multitasking_class(self):
        """
        Get the class representing either a thread or process based on the multitasking type.
        """
        if self.multitasking_type == ConcurrencyType.THREADS:
            import threading as multitasking
            task_class = multitasking.Thread
        else:
            import multiprocessing as multitasking
            task_class = multitasking.Process

        return task_class

    def _run_body(self):
        self.logger().info(f'BEGIN {self.name()}')
        self._tasks = self._get_tasks()  # adds type of concurrency to workers
        try:
            self._run_all()
            self._join_all()
        finally:
            self.set_stop_event_to_stop()
            self.logger().info(f'END {self.name()}')

    def _run_all(self):
        """
        Start all worker tasks.
        """
        for p in self._tasks:
            p.start()

    def _join_all(self):
        """
        Wait for all worker tasks to complete.
        """
        for p in self._tasks:
            p.join()

    def _get_tasks(self) -> ['self._TaskClass']:
        """
        Create task instances for each worker based on the multitasking type.
        """
        tasks = []
        for worker in self._workers:
            worker.set_multitasking_type(multitasking_type=self.multitasking_type)
            tasks.append(self._TaskClass(target=worker.run))
        return tasks

    @staticmethod
    def get_queue_log_processor(
            filename: str,
            multitasking_type: ConcurrencyType = ConcurrencyType.PROCESSES
    ) -> (LogQueueStreamProcessor, multiprocessing.Queue):
        """
        Returns a processor which can be used in src.runner.ProcessorsRunner to run in a separate
        process/thread.
        Sets logging handler to store logs in a shared queue.
        """
        queue = multiprocessing.Queue()  # store queue in the current context
        processor = LogQueueStreamProcessor(name='LogManager', queue=queue, filename=filename)
        LogManager.set_queue_as_logger(queue=queue, multitasking_type=multitasking_type, use_formatter=False)
        return processor, queue
