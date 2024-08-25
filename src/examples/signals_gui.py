#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Runs:
    1) A process with a GUI that has three buttons for sending inter-process signals.
       Pressing a button sends the corresponding signal to the second process ("Activate", "Deactivate", "Stop All").
       It also includes status indicators that loop to read status from files. 
       This status is modified by other processes (see below).

    2) Another process with multiple subprocesses and threads. 
       The abstraction of a process or thread is an instance of the Processor class (or its subclass).
       The top-level process in the hierarchy receives the signals mentioned above from the GUI.

    Each of these processors reacts to the "Activate" and "Deactivate" signals by:
        a) Changing its state.
        b) Writing its activity to a file (which is then read by the "indicators" in the GUI, as mentioned above).

    Output is logged to the file signals_gui.py.log.txt.

    Standard signals from the signal module are used (not user-defined signals from src/concurrency/signals/multiproc_user_signals.py).
'''

import tkinter as tk
from tkinter import ttk
import os
import time
import threading
import logging

# Root of project repository
from git_root_to_syspath import agr;

PROJECT_ROOT = agr()
from src.loop_processor import LoopProcessor
from src.concurrency_types import ConcurrencyType
from src.runner import ProcessorsRunner
import multiprocessing
from src.run.rpi.signals import SignalsEnum
from src.log.log_manager import LogManager
from src.state_in_file import StateInFile

StateInFile._ROOT_DIR = os.path.dirname(__file__)


# --- GUI --------------------------------------------------------------------------------------------------------------

class GuiProcessor(StateInFile):
    """
    Abstraction of a process that reads its state from a file and displays it in the GUI.
    """
    width = 15

    def __init__(self, name: str, gui_root: tk.Tk):
        self._name = name
        self._gui_root = gui_root
        self._state = self.read_state(self._name)
        self._label = tk.Label(
            gui_root, text=self._get_text(), width=self.width, height=2, foreground='white',
            background=self._get_color())

    def _get_color(self):
        if self._state == 'active':
            return 'green'
        else:
            return 'blue'

    def _get_text(self):
        return f'{self._name}: {self._state}'

    def get_label(self):
        return self._label

    def update(self):
        self._state = self.read_state(self._name)
        self._label.config(text=self._get_text(), background=self._get_color())


class Gui:
    """
    The entire GUI with multiple processors.
    """
    padx = 30
    pady = 30

    def __init__(self, target_pid=None):
        self._target_pid = target_pid
        self._gui_processors = []
        self._root = tk.Tk()
        self._root.title("Simple GUI with LEDs")
        self._last_column = 0
        style = ttk.Style()
        style.configure('Red.TButton', background='red', foreground='white')
        style.map('Red.TButton', background=[('active', 'dark red')])

        style.configure('Green.TButton', background='green', foreground='white')
        style.map('Green.TButton', background=[('active', 'dark green')])

        style.configure('Blue.TButton', background='blue', foreground='white')
        style.map('Blue.TButton', background=[('active', 'dark blue')])
        self._add_buttons()

    def _add_buttons(self):
        # Creating buttons
        button1 = ttk.Button(self._root, text="Activate", command=self._activate, style='Green.TButton')
        button1.grid(row=1, column=0, padx=self.padx, pady=self.pady)

        button2 = ttk.Button(self._root, text="Deactivate", command=self._deactivate, style='Blue.TButton')
        button2.grid(row=1, column=1, padx=self.padx, pady=self.pady)

        button3 = ttk.Button(self._root, text="Stop All", command=self._stop_all, style='Red.TButton')
        button3.grid(row=1, column=2, padx=self.padx, pady=self.pady)

    def _send_signal(self, signal):
        try:
            print('send signal', signal, 'to', self._target_pid)
            os.kill(self._target_pid, signal)
        except Exception as e:
            print('Error:', e)

    def _activate(self):
        print('activate all')
        self._send_signal(SignalsEnum.ACTIVATE.value)

    def _deactivate(self):
        print('deactivate all')
        self._send_signal(SignalsEnum.DEACTIVATE.value)

    def _stop_all(self):
        print('stop all')
        self._send_signal(SignalsEnum.TERMINATE_ALL.value)
        self._root.destroy()

    def add_processor(self, name: str):
        processor = GuiProcessor(name, self._root)
        label = processor.get_label()
        label.grid(row=0, column=self._last_column, padx=self.padx, pady=self.pady)
        self._gui_processors.append(processor)
        self._last_column += 1

    def update_processors(self):
        while True:
            for processor in self._gui_processors:
                processor.update()
            time.sleep(0.2)

    def run(self):
        # Start the thread to update LED states
        threading.Thread(target=self.update_processors, daemon=True).start()
        self._root.mainloop()


# --- Independent processes and threads controlled by signals from the GUI --------------------------------------------

# Names of the processes
processors_names = ['P 1', 'P 2.1', 'P 2.2']


class LoopProcessorShowStateInFile(LoopProcessor, StateInFile):
    """
    Processor that repeatedly writes its activity state to a file.
    """

    def __init__(self, name: str, sleep_s: float = 0.1, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._sleep_s = sleep_s

    def _became_active(self):
        self._write_state(self.name(), True)
        self.logger().debug(f'{self.name()} became active')
        time.sleep(self._sleep_s)

    def _became_inactive(self):
        self._write_state(self.name(), False)
        self.logger().debug(f'{self.name()} became inactive')
        time.sleep(self._sleep_s)


class ExampleRunner(ProcessorsRunner):
    """
    Example runner that orchestrates the independent processes and threads.
    """

    def __init__(self, name: str, logging_level: int = logging.DEBUG, *args, **kwargs):
        LogManager.set_logging_level(logging_level=logging_level)
        filename = os.path.join('.', os.path.basename(__file__) + '.log.txt')
        print(f'The log file: {filename} ({os.path.abspath(filename)})')
        time.sleep(0.1)

        logger_processor, log_queue = self.get_queue_log_processor(
            filename=filename,
            multitasking_type=ConcurrencyType.PROCESSES
        )

        # Shared event for all processors
        self._is_waiting_event = multiprocessing.Event()

        super().__init__(
            multitasking_type=ConcurrencyType.PROCESSES,
            workers=[
                logger_processor,
                LoopProcessorShowStateInFile(name=processors_names[0], is_waiting_event=self._is_waiting_event),
                # Subprocess with two threads
                ProcessorsRunner(
                    multitasking_type=ConcurrencyType.THREADS,
                    workers=[
                        LoopProcessorShowStateInFile(name=processors_names[1], is_waiting_event=self._is_waiting_event),
                        LoopProcessorShowStateInFile(name=processors_names[2], is_waiting_event=self._is_waiting_event)
                    ],
                    name='switch_activities',
                ),
            ],
            name=name,
            *args,
            **kwargs
        )

        def register_signals(self):
            super().register_signals()
            self._register_signal(SignalsEnum.ACTIVATE, self.activate_me)
            self._register_signal(SignalsEnum.DEACTIVATE, self.deactivate_me)

        def activate_me(self):
            self.logger().info(f'{self.name()} ACTIVATE signal received')
            self._is_waiting_event.set()

        def deactivate_me(self):
            self.logger().info(f'{self.name()} DEACTIVATE signal received')
            self._is_waiting_event.clear()


def target_process():
    runner = ExampleRunner(name='ExampleRunner', logging_level=logging.DEBUG, stop_event=multiprocessing.Event())
    runner.run()


def gui_process(pid):
    gui = Gui(target_pid=pid)
    for name in processors_names:
        gui.add_processor(name)
    gui.run()


if __name__ == '__main__':
    p1 = multiprocessing.Process(target=target_process)
    p1.start()

    print('PID:', p1.pid)

    p2 = multiprocessing.Process(target=gui_process, args=(p1.pid,))
    p2.start()

    p1.join()
    p2.join()
