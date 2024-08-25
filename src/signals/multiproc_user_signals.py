#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Enables the use of an arbitrary number of signals in both Linux and Windows environments.
    It utilizes the SIGINT signal and a context that is stored in a temporary file.
    This file contains an expanding signal number from zero to 65536.
'''

import tempfile
import os
import math
import struct
import time
import types
import signal
import multiprocessing
from typing import Dict, Callable
from enum import Enum, auto
from collections.abc import Sized
import fcntl

from git_root_to_syspath import agr; PROJECT_ROOT = agr()

from src.processor import Processor


class UserSignals(Enum):
    ACTIVATE = auto()
    DEACTIVATE = auto()


class SignalContext:
    """
    Manages a signal context that supports the use of custom signals across platforms.
    """
    COMMON_SIGNAL = signal.SIGUSR1

    def __init__(self, context_name: str = 'default', signals: Sized = UserSignals):
        range_max: int = len(signals)
        temp_dir = tempfile.gettempdir()
        self._filename = os.path.join(temp_dir, context_name + '.signal_context')
        self._struct_format = self.get_struct_format(range_max)

    def _get_filename(self):
        return self._filename

    @staticmethod
    def get_struct_format(range_max: int) -> str:
        """
        Determine the appropriate struct format based on the range of signal values.
        """
        if range_max < 0:
            raise ValueError("range_max must be non-negative")

        num_bits = math.ceil(math.log2(range_max + 1))

        if num_bits <= 8:
            return 'B'  # Unsigned byte
        elif num_bits <= 16:
            return 'H'  # Unsigned short
        elif num_bits <= 32:
            return 'I'  # Unsigned int
        elif num_bits <= 64:
            return 'Q'  # Unsigned long long
        else:
            raise ValueError("range_max is too large to be handled by struct module")

    def get_signal(self) -> int:
        """
        Retrieve the signal value from the context file.
        """
        ret_val = None
        try:
            with open(self._filename, 'r+b') as f:
                try:
                    fcntl.flock(f, fcntl.LOCK_EX)  # Lock file
                    data = f.read()
                    os.remove(self._filename)  # Invalidate signal for next time
                    ret_val = struct.unpack(self._struct_format, data)[0]
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)  # Unlock file
        finally:
            return ret_val

    def set_signal_id(self, signal: int):
        """
        Write a signal value to the context file.
        """
        with open(self._filename, 'wb') as f:
            f.write(struct.pack(self._struct_format, signal))

    def send_user_signal(self, pid: int, signal: int) -> None:
        """
        Send a user-defined signal to the specified process.
        """
        self.set_signal_id(signal)
        os.kill(pid, self.COMMON_SIGNAL)

    def register_signals(self, signal_handler: Callable[[int, types.FrameType], None]):
        """
        Register the common signal with the specified handler.
        """
        signal.signal(self.COMMON_SIGNAL, signal_handler)


class UserSignalConsumerProcessor(Processor):
    """
    A processor that can handle user-defined signals using a SignalContext.
    """

    def __init__(self, signal_context: SignalContext = SignalContext(), *args, **kwargs):
        self._signal_context = signal_context
        super().__init__(*args, **kwargs)

    def on_user_signal(
            self,
            user_signal_id: int,
            frame: types.FrameType,
            common_signal_id: int = SignalContext.COMMON_SIGNAL
    ):
        """
        Handle a user-defined signal.
        Must be implemented in subclasses.
        """
        raise NotImplementedError('on_user_signal must be implemented in subclass')

    def on_common_signal(self, common_signal_id: int, frame: types.FrameType):
        """
        Handle the common signal and map it to a user-defined signal.
        """
        user_signal = self._signal_context.get_signal()
        print(f'on_common_signal(user_signal: {user_signal}, common_signal: {common_signal_id})\n')
        if user_signal is not None:
            self.on_user_signal(user_signal, frame, common_signal_id)

    def register_signals(self):
        """
        Register the common signal handler.
        """
        super().register_signals()
        try:
            self._signal_context.register_signals(self.on_common_signal)
        except Exception as e:
            print(f"Error registering signals: {e}")
            self.logger().exception(e)


class UserSignalProducer:
    """
    A class that sends user-defined or standard signals to a process.
    """

    def __init__(self, signal_context: SignalContext = SignalContext(), *args, **kwargs):
        self._signal_context = signal_context

    def send_user_signal(self, pid: int, signal: int):
        """
        Send a user-defined signal to the given process.
        """
        self._signal_context.send_user_signal(pid, signal)

    def send_standard_signal(self, pid: int, signal: int):
        """
        Send a standard signal (from the signal module) to the given process.
        """
        try:
            os.kill(pid, signal)
        except Exception as e:
            print('Error:', e)


if __name__ == '__main__':
    # For full example of usage @see src/concurrency/examples/user_signals_gui.py

    import multiprocessing

    class MyUserSignals(Enum):
        ACTIVATE_DATA_READING = auto()
        DEACTIVATE_DATA_READING = auto()
        ACTIVATE_DATA_STORING = auto()
        DEACTIVATE_DATA_STORING = auto()

    class MySignalContext(SignalContext):
        def __init__(self):
            super().__init__(context_name='my_signals', signals=MyUserSignals)

    class MyUserSignalConsumerProcessor(UserSignalConsumerProcessor):
        i = 0

        def __init__(self, *args, **kwargs):
            super().__init__(stop_event=multiprocessing.Event(), *args, **kwargs)

        def on_user_signal(
                self,
                user_signal_id: int,
                frame: types.FrameType,
                common_signal_id: int = SignalContext.COMMON_SIGNAL
        ):
            print(f'{self.i}# on_user_signal(user_signal: {user_signal_id} {MyUserSignals(user_signal_id).name}, '
                  f'common_signal: {common_signal_id}, frame:{frame})\n')
            self.i += 1

        def _run_body(self):
            while not self._stop_event.is_set():
                time.sleep(0.1)

    class MyUserSignalProducer(UserSignalProducer):

        def run(self, consumer_pid: int = None):
            print(f'MyUserSignalProducer.run(consumer_pid={consumer_pid})')
            time.sleep(0.4)  # Wait for consumer to start
            self.send_user_signal(consumer_pid, MyUserSignals.ACTIVATE_DATA_READING.value)
            time.sleep(0.1)
            self.send_user_signal(consumer_pid, MyUserSignals.DEACTIVATE_DATA_READING.value)
            time.sleep(0.1)
            self.send_user_signal(consumer_pid, MyUserSignals.ACTIVATE_DATA_STORING.value)
            time.sleep(0.1)
            self.send_user_signal(consumer_pid, MyUserSignals.DEACTIVATE_DATA_STORING.value)
            time.sleep(0.1)
            os.kill(consumer_pid, signal.SIGTERM)

    def consumer_process():
        consumer = MyUserSignalConsumerProcessor(signal_context=MySignalContext())
        consumer.run()

    def producer_process(consumer_pid: int):
        producer = MyUserSignalProducer(signal_context=MySignalContext())
        producer.run(consumer_pid)

    def run_all():
        consumer = multiprocessing.Process(target=consumer_process)
        consumer.start()

        print('consumer.pid:', consumer.pid)
        print()

        producer = multiprocessing.Process(target=producer_process, args=(consumer.pid,))
        producer.start()

        consumer.join()

    run_all()
