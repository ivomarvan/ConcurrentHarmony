#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

__author__ = 'Ivo Marvan'
__email__ = 'ivo@marvan.cz'
__description__ = '''
    Runs multiple simple loop processors in multiple processes and threads.
    
    This is a specific example that uses parts of code from another project (access to the CAN bus, etc.). 
    It is provided for demonstration purposes only and cannot be run independently.
'''

import os
import logging
from time import sleep

# Root of project repository
from git_root_to_syspath import agr; PROJECT_ROOT = agr()

from src.concurrency_types import ConcurrencyType
from src.loop_processor import LoopProcessor
from src.runner import ProcessorsRunner
from src.log.log_manager import LogManager

NOGIT_DATA = os.path.join(PROJECT_ROOT, 'nogit_data')
DEFAULT_OUT_DIR = os.path.join(NOGIT_DATA, 'LOG')


class SleepProcessor(LoopProcessor):
    """
    A processor that simulates work by sleeping for a specified time.
    """

    def __init__(self, name: str, sleep_time: float, number_of_after_life_messages: int = 3, *args, **kwargs):
        super().__init__(name=name, *args, **kwargs)
        self._sleep_time = sleep_time
        self._number_of_after_life_messages = number_of_after_life_messages

    def _before_body(self):
        self.logger().debug(f'{self.name()}._before_body')

    def _after_body(self):
        self.logger().debug(f'{self.name()}._after_body')
        for i in range(self._number_of_after_life_messages):
            self.logger().info(f'{self.name()}: {i}. after life message')
            sleep(self._sleep_time)

    def _work_in_loop(self):
        self.logger().debug(f'{self.name()}._work_in_loop 1')
        sleep(self._sleep_time)
        self.logger().debug(f'{self.name()}._work_in_loop 2')


class RunAll(ProcessorsRunner):
    """
    Configured singleton for running processors in processes and threads.
    """

    def __init__(
            self,
            logging_level: int = logging.INFO,
    ):
        LogManager.set_logging_level(logging_level=logging_level)

        logger_processor, log_queue = self.get_queue_log_processor(
            filename=os.path.join(DEFAULT_OUT_DIR, 'ERR.log.txt'),
            multitasking_type=ConcurrencyType.PROCESSES
        )

        # Register signal handlers (especially TERMINATE)
        self.register_signals()

        first_threads = [
            SleepProcessor(name='A1', sleep_time=0.2),
            SleepProcessor(name='A2', sleep_time=0.1),
            SleepProcessor(name='A3', sleep_time=0.15)
        ]

        second_threads = [
            SleepProcessor(name='B1', sleep_time=0.2),
            SleepProcessor(name='B2', sleep_time=0.1)
        ]

        running_processes = [
            logger_processor,

            ProcessorsRunner(
                multitasking_type=ConcurrencyType.THREADS,
                workers=first_threads,
                name='A',
            ),

            ProcessorsRunner(
                multitasking_type=ConcurrencyType.THREADS,
                workers=second_threads,
                name='B',
            )
        ]

        super().__init__(
            multitasking_type=ConcurrencyType.PROCESSES,
            workers=running_processes,
            name='main',
        )

    def run(self):
        pid = os.getpid()
        self.logger().info(f'Starting main process PID={pid}\nKill it by:\n\t kill -15 {pid}\n\n')
        super().run()


from src.can_bus.hw_db import get_hw_can_bus, HwImplementations, CanConfig, HwCanWithDatabase

def _before_main():
    can_bus_config = CanConfig(
        device='/dev/ttyUSB0', baudrate=115200,  # Params for RpcCanBus and ArduinoMcp2512CanBus
        hw_type=HwImplementations.rpi_rs485_can_hat,
        channel='can0', bitrate=int(1e6), receive_own_messages=True,  # Params for SocketCanBus
    )
    can_bus = get_hw_can_bus(can_bus_config=can_bus_config)  # Get the CAN bus object based on the configuration
    can_bus.up(can_bus_config=can_bus_config)  # Initialize CAN bus hardware
    can_bus.open()  # Open the bus, providing access to the specific object (e.g., socket)
    return can_bus, can_bus_config

def _after_main(can_bus: HwCanWithDatabase, can_bus_config):
    can_bus.close()
    can_bus.down(can_bus_config=can_bus_config)


def main(logging_level: int = logging.INFO):
    main_process = RunAll(logging_level=logging_level)

    can_bus, can_bus_config = _before_main()  # Investigating what breaks logging

    try:
        main_process.run()
    except Exception as e:
        main_process.logger().critical(f'Exception occurred {e}', exc_info=True)
    finally:
        _after_main(can_bus=can_bus, can_bus_config=can_bus_config)  # Investigating what breaks logging
        main_process.logger().info('Main process finished')


if __name__ == '__main__':
    main(logging_level=logging.INFO)
