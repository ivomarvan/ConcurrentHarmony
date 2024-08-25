#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Shared variables for communication between processes and threads.
    A faster implementation uses multiprocessing.Value and multiprocessing.Array,
    while a slower one uses multiprocessing.Manager().Namespace().

    Currently, only the necessary flags are used via multiprocessing.Array.
'''

import ctypes
from multiprocessing import Array, Manager


def multi_proc_bool_array(attributes, index_from: int = 0):
    """
    Decorator for a class that should have shared boolean flags.
    Faster implementation using multiprocessing.Array.
    """

    def class_decorator(cls):
        if isinstance(attributes, list):
            attribute_names = attributes
            default_values = [False] * len(attribute_names)
        elif isinstance(attributes, dict):
            attribute_names = list(attributes.keys())
            default_values = list(attributes.values())
        else:
            raise ValueError("Attributes must be either a list of names or a dictionary of name: default_value pairs.")

        cls._array = Array(ctypes.c_bool, default_values)

        def make_getter(idx):
            def getter(self):
                with self._array.get_lock():
                    return self._array[idx]

            return getter

        def make_setter(idx):
            def setter(self, value):
                with self._array.get_lock():
                    self._array[idx] = value

            return setter

        for index_shift, name in enumerate(attribute_names):
            index = index_from + index_shift
            getter = make_getter(index)
            setter = make_setter(index)
            prop = property(getter, setter)
            setattr(cls, name, prop)

        return cls

    return class_decorator


def multi_proc_bool_array_namespace(attributes):
    """
    Decorator for a class that should have shared boolean flags.
    Slower implementation using multiprocessing.Manager().Namespace().
    """

    def class_decorator(cls):
        manager = Manager()
        cls._namespace = manager.Namespace()

        if isinstance(attributes, list):
            attribute_names = attributes
            default_values = [False] * len(attribute_names)
        elif isinstance(attributes, dict):
            attribute_names = list(attributes.keys())
            default_values = list(attributes.values())
        else:
            raise ValueError("Attributes must be either a list of names or a dictionary of name: default_value pairs.")

        for name, default in zip(attribute_names, default_values):
            setattr(cls._namespace, name, default)

        def make_getter(name):
            def getter(self):
                return getattr(self._namespace, name)

            return getter

        def make_setter(name):
            def setter(self, value):
                setattr(self._namespace, name, value)

            return setter

        for name in attribute_names:
            getter = make_getter(name)
            setter = make_setter(name)
            prop = property(getter, setter)
            setattr(cls, name, prop)

        return cls

    return class_decorator


if __name__ == '__main__':
    # Test the speed of both approaches

    import time
    import threading
    import multiprocessing


    def usage_example():
        # Faster implementation using multiprocessing.Array
        @multi_proc_bool_array(['is_active', 'is_updated', 'is_locked'])
        class SharedBoolArray:
            pass

        @multi_proc_bool_array({'is_active': True, 'is_updated': False, 'is_locked': True})
        class SharedBoolArrayWithDefaults:
            pass

        # Testing the class without default values
        obj1 = SharedBoolArray()
        print(obj1.is_active)  # Prints 'False'
        obj1.is_active = True
        print(obj1.is_active)  # Prints 'True'

        # Testing the class with default values
        obj2 = SharedBoolArrayWithDefaults()
        print(obj2.is_active)  # Prints 'True'
        print(obj2.is_updated)  # Prints 'False'

        # ----------------------------------------------
        # Slower implementation using multiprocessing.Manager().Namespace()
        @multi_proc_bool_array_namespace(['is_active', 'is_updated', 'is_locked'])
        class SharedBoolNamespaceArray:
            pass

        @multi_proc_bool_array_namespace({'is_active': True, 'is_updated': False, 'is_locked': True})
        class SharedBoolNamespaceArrayWithDefaults:
            pass

        # Testing the class without default values
        obj1 = SharedBoolNamespaceArray()
        print(obj1.is_active)  # Prints 'False'
        obj1.is_active = True
        print(obj1.is_active)  # Prints 'True'

        # Testing the class with default values
        obj2 = SharedBoolNamespaceArrayWithDefaults()
        print(obj2.is_active)  # Prints 'True'
        print(obj2.is_updated)  # Prints 'False'


    def speed_test():
        @multi_proc_bool_array(['is_active'])
        class SharedBoolArray:
            pass

        @multi_proc_bool_array_namespace(['is_active'])
        class SharedBoolNamespaceArray:
            pass

        def toggle_flag(obj, num_iterations):
            for _ in range(num_iterations):
                current = obj.is_active
                obj.is_active = not current

        def run_test(use_multiprocessing, num_operations, num_iterations):
            Process = multiprocessing.Process if use_multiprocessing else threading.Thread

            obj1 = SharedBoolArray()
            obj2 = SharedBoolNamespaceArray()

            start_time = time.time()
            processes = [Process(target=toggle_flag, args=(obj1, num_iterations)) for _ in range(num_operations)]
            for p in processes:
                p.start()
            for p in processes:
                p.join()
            array_time = time.time() - start_time

            start_time = time.time()
            processes = [Process(target=toggle_flag, args=(obj2, num_iterations)) for _ in range(num_operations)]
            for p in processes:
                p.start()
            for p in processes:
                p.join()
            namespace_time = time.time() - start_time

            print(
                f"{'Multiprocessing' if use_multiprocessing else 'Threading'} test with {num_operations} processes/threads:")
            print(f"SharedBoolArray time: {array_time:.6f}s")
            print(f"SharedBoolNamespaceArray time: {namespace_time:.6f}s")
            print(f"SharedBoolArray is faster than SharedBoolNamespaceArray {namespace_time / array_time:.2f}x")
            print()

        # Example usage
        run_test(use_multiprocessing=True, num_operations=10, num_iterations=10000)
        run_test(use_multiprocessing=False, num_operations=10, num_iterations=10000)


    usage_example()
    print('-' * 80)
    speed_test()
