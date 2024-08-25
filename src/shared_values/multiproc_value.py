#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Wrapper for multiprocessing.Value
'''

import multiprocessing


class MultiprocessingValue:
    """
    A wrapper around multiprocessing.Value that provides type inference and locking.
    """

    @classmethod
    def get_value_type(cls, value):
        """
        Determine the appropriate type code for multiprocessing.Value based on the given value.
        """
        if isinstance(value, int):
            if -(2 ** 31) <= value <= (2 ** 31 - 1):
                return 'i'  # Signed int
            elif 0 <= value <= (2 ** 32 - 1):
                return 'I'  # Unsigned int
            elif -(2 ** 63) <= value <= (2 ** 63 - 1):
                return 'q'  # Signed long long
            elif 0 <= value <= (2 ** 64 - 1):
                return 'Q'  # Unsigned long long
            else:
                raise ValueError("Integer value out of range for supported types.")
        elif isinstance(value, float):
            return 'd'  # Double
        elif isinstance(value, bytes) and len(value) == 1:
            return 'c'  # Char
        else:
            raise TypeError("Unsupported type for multiprocessing.Value.")

    def __init__(self, value=None, forced_type=None, shared_value: multiprocessing.Value = None):
        """
        Initialize a MultiprocessingValue instance. If no shared_value is provided, create a new one.
        """
        if shared_value is None:
            if forced_type is None:
                forced_type = self.get_value_type(value)
            shared_value = multiprocessing.Value(forced_type, value)
        self._wrapper = shared_value

    @property
    def value(self):
        """
        Get the value, ensuring thread safety with a lock.
        """
        with self._wrapper.get_lock():
            return self._wrapper.value

    @value.setter
    def value(self, new_value):
        """
        Set the value, ensuring thread safety with a lock.
        """
        with self._wrapper.get_lock():
            self._wrapper.value = new_value

    @property
    def wrapper(self):
        """
        Access the underlying multiprocessing.Value object.
        """
        return self._wrapper


class LabeledMultiprocValue(MultiprocessingValue):
    """
    A container for multiprocessing.Value with additional attributes (label, threshold, last_value).
    """

    def __init__(self, shared_value: multiprocessing.Value, label: str, threshold: int = 0, *args, **kwargs):
        super().__init__(shared_value=shared_value, *args, **kwargs)
        self.label = label
        self.threshold = threshold
        self.last_value = shared_value.value


if __name__ == '__main__':
    # Example of usage
    import time
    import random

    count = MultiprocessingValue(0)
    count_of_processes = 8

    def worker(shared_value_wrapper, name: str):
        """
        Worker function that increments the shared value and prints its status.
        """
        for _ in range(5):
            shared_value_wrapper.value += 1
            print(f"Worker {name}: {shared_value_wrapper.value}")
            sleep_time = random.random() / 10
            time.sleep(sleep_time)

    processes = []
    for pi in range(count_of_processes):
        p = multiprocessing.Process(target=worker, args=(count, f'p{pi}'))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()

    print(f"\nFinal value: {count.value}")
