#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Interface and handling for logging from multiple processes/threads.
    Messages are stored in a single queue and read from it in one process, where they are written to stdout.
'''

import multiprocessing
import queue
from logging.handlers import QueueHandler
import logging
from time import sleep

# Root of project repository
from git_root_to_syspath import agr; PROJECT_ROOT = agr()
from src.log.log_access import LoggerAccess
from src.concurrency_types import ConcurrencyType


class LogManager(LoggerAccess):
    """
    Manages logging from multiprocessing/threading.
    For more details, see:
    - https://superfastpython.com/multiprocessing-logging-in-python/
    - https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes
    """
    __common_logging_queue: multiprocessing.Queue = None
    __log_stream = None
    __last_log_filename = None
    _LOGGING_LEVEL = logging.DEBUG
    _LOGGING_FORMAT = {}
    __log_format_prefix = '[%(levelname)s]\t%(asctime)s.%(msecs)03d:\t"%(message)s"'
    __log_format_sufix = '\t%(module)s(%(lineno)d).%(funcName)s\t[%(pathname)s]'
    _LOGGING_FORMAT[ConcurrencyType.PROCESSES] = \
        __log_format_prefix + '\t%(processName)s\t%(threadName)s' + __log_format_sufix
    _LOGGING_FORMAT[ConcurrencyType.THREADS] = \
        __log_format_prefix + '\t%(threadName)s' + __log_format_sufix
    _LOGGING_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    @classmethod
    def stop_logging(cls):
        """
        Stop the logging by sending a termination signal (None) to the queue.
        """
        if cls.__common_logging_queue is not None:
            cls.__common_logging_queue.put(None)

    @classmethod
    def get_stream_logger(
        cls,
        filename: str,
        name: str = 'app',
        multitasking_type: ConcurrencyType = ConcurrencyType.PROCESSES,
        use_formatter: bool = True
    ):
        """
        Returns a StreamHandler that logs to a specified file.
        """
        if cls.__log_stream is None or filename != cls.__last_log_filename:
            cls.__log_stream = open(filename, 'w')
            cls.__last_log_filename = filename
        stream_handler = logging.StreamHandler(cls.__log_stream)
        logger = cls.__init_logger_by_handler(
            handler=stream_handler, name=name, multitasking_type=multitasking_type,
            use_formatter=use_formatter
        )
        cls.__log_stream.flush()
        return logger

    @classmethod
    def set_queue_as_logger(
        cls,
        queue: multiprocessing.Queue | queue.Queue,
        name: str = 'app',
        multitasking_type: ConcurrencyType = ConcurrencyType.PROCESSES,
        use_formatter: bool = True
    ):
        """
        Sets a queue as the logging target using a QueueHandler.
        """
        cls.__common_logging_queue = queue
        cls._logger = cls.__init_logger_by_handler(
            QueueHandler(queue), name=name, multitasking_type=multitasking_type, use_formatter=use_formatter
        )

    @classmethod
    def __init_logger_by_handler(
        cls,
        handler: logging.Handler,
        name: str = 'app',
        multitasking_type: ConcurrencyType = ConcurrencyType.PROCESSES,
        use_formatter: bool = True
    ):
        """
        Initialize a logger with a specified handler and configure it.
        """
        if use_formatter:
            formatter = logging.Formatter(cls._LOGGING_FORMAT[multitasking_type], datefmt=cls._LOGGING_DATETIME_FORMAT)
            handler.setFormatter(formatter)
        logger = logging.getLogger(name)
        if not logger.hasHandlers():
            logger.addHandler(handler)
        logger.setLevel(cls._LOGGING_LEVEL)
        return logger

    @classmethod
    def set_logging_level(cls, logging_level: int):
        """
        Set the logging level for the logger.
        """
        cls._LOGGING_LEVEL = logging_level

    @classmethod
    def destroy(cls, names: [str] = ['app', 'queue->stream']):
        """
        Stop logging and clean up logger resources.
        """
        cls.stop_logging()  # Stop logging
        sleep(0.2)
        for name in names:
            logger = logging.getLogger(name)
            list(map(logger.removeHandler, logger.handlers))
            list(map(logger.removeFilter, logger.filters))
        if cls.__common_logging_queue is not None:
            del cls.__common_logging_queue
            cls.__common_logging_queue = None
