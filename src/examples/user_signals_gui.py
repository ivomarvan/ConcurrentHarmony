#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Uses user-defined signals from src/concurrency/signals/multiproc_user_signals.py.

    1) A process with a GUI that has five buttons for sending user-defined inter-process signals:
    - "Activate Data Acquisition"
    - "Deactivate Data Acquisition"
    - "Activate Data Storage"
    - "Deactivate Data Storage"
    - "Stop All"
    Pressing a button sends the corresponding signal to the second process.
    The GUI also includes indicators of the states of other processors that receive the signals.
    The states of the monitored processors are read in a loop from files in the GUI.

    2) Another process with multiple subprocesses and threads. 
       The abstraction of a process or thread is an instance of the Processor class (or its subclass).
       The top-level process (ExampleRunner) receives the signals from the GUI.
       This processor reacts to all the signals by changing the corresponding event states 
       (*_is_waiting_event), thereby changing the activity of its subprocessors (LoopProcessorShowStateInFile).

    Output is logged to the file user_signals_gui.py.log.txt.
    States are passed via files with the .state extension.
'''

import tkinter as tk
from tkinter import ttk
from tkinter import font
import os
import time
import threading
import types
import logging
from enum import Enum, auto
import signal

# Root of project repository
from git_root_to_syspath import agr;

PROJECT_ROOT = agr()
from src.loop_processor import LoopProcessor
from src.concurrency_types import ConcurrencyType
from src.runner import ProcessorsRunner
import multiprocessing
from src.log.log_manager import LogManager
from src.signals.multiproc_user_signals import SignalContext, UserSignalConsumerProcessor, \
    UserSignalProducer
from src.state_in_file import StateInFile

StateInFile._ROOT_DIR = os.path.dirname(__file__)


# --- User signals ----------------------------------------------------------------------------------------------------


class MyUserSignals(Enum):
    ACTIVATE_DATA_READING = auto()
    DEACTIVATE_DATA_READING = auto()
    ACTIVATE_DATA_STORING = auto()
    DEACTIVATE_DATA_STORING = auto()


class MySignalContext(SignalContext):
    def __init__(self):
        super().__init__(context_name='my_signals', signals=MyUserSignals)


# --- GUI --------------------------------------------------------------------------------------------------------------
class GuiProcessor(StateInFile):
    """
    Abstraction of a process that reads its state from a file and displays it in the GUI.
    """
    width = 20

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


class Gui(UserSignalProducer):
    """
    The entire GUI with multiple processors.
    """
    padx = 30
    pady = 30

    def __init__(self, target_pid=None, signal_context: SignalContext = MySignalContext(), *args, **kwargs):
        self._target_pid = target_pid
        self._gui_processors = []
        self._root = tk.Tk()
        self._root.title("Example of using user signals to control activity state of processes")
        self._last_column = 0
        style = ttk.Style()

        style.configure(
            'Red.TButton', background='red', foreground='white',
            padding=5, relief='raised', borderwidth=3, focusthickness=3, focuscolor='red'
        )
        style.map('Red.TButton', background=[('active', 'dark red')])

        style.configure(
            'Green.TButton', background='green', foreground='white',
            padding=5, relief='raised', borderwidth=3, focusthickness=3, focuscolor='red'
        )
        style.map('Green.TButton', background=[('active', 'dark green')])

        style.configure(
            'Blue.TButton', background='blue', foreground='white',
            padding=5, relief='raised', borderwidth=3, focusthickness=3, focuscolor='red'
        )
        style.map('Blue.TButton', background=[('active', 'dark blue')])
        self._add_buttons()
        super().__init__(signal_context=signal_context, *args, **kwargs)

    def _add_buttons(self):
        bold_font = font.Font(family="Helvetica", size=12, weight="bold")

        # Creating labels
        tk.Label(self._root, text="Data Acquisition", width=15, height=2, foreground='black', font=bold_font) \
            .grid(row=0, column=0, padx=self.padx, pady=self.pady)

        tk.Label(self._root, text="Data Storage", width=15, height=2, foreground='black', font=bold_font) \
            .grid(row=0, column=1, padx=self.padx, pady=self.pady)

        # Creating buttons
        #   Data Acquisition
        ttk.Button(
            self._root, text="Activate Data Acquisition", command=self._activate_data_acquisition,
            style='Green.TButton'
        ).grid(row=1, column=0, padx=self.padx, pady=self.pady)

        ttk.Button(
            self._root, text="Deactivate Data Acquisition", command=self._deactivate_data_acquisition,
            style='Blue.TButton'
        ).grid(row=2, column=0, padx=self.padx, pady=self.pady)
        #   Data Storage
        ttk.Button(
            self._root, text="Activate Data Storage", command=self._activate_data_storage,
            style='Green.TButton'
        ).grid(row=1, column=1, padx=self.padx, pady=self.pady)

        ttk.Button(
            self._root, text="Deactivate Data Storage", command=self._deactivate_data_storage,
            style='Blue.TButton'
        ).grid(row=2, column=1, padx=self.padx, pady=self.pady)

        ttk.Button(
            self._root, text="Stop All", command=self._stop_all, style='Red.TButton'
        ).grid(row=1, column=2, padx=self.padx, pady=self.pady)

    def _activate_data_acquisition(self):
        print('send signal', MyUserSignals.ACTIVATE_DATA_READING.name, 'to', self._target_pid)
        self.send_user_signal(self._target_pid, MyUserSignals.ACTIVATE_DATA_READING.value)

    def _deactivate_data_acquisition(self):
        print('send signal', MyUserSignals.DEACTIVATE_DATA_READING.name, 'to', self._target_pid)
        self.send_user_signal(self._target_pid, MyUserSignals.DEACTIVATE_DATA_READING.value)

    def _activate_data_storage(self):
        print('send signal', MyUserSignals.ACTIVATE_DATA_STORING.name, 'to', self._target_pid)
        self.send_user_signal(self._target_pid, MyUserSignals.ACTIVATE_DATA_STORING.value)

    def _deactivate_data_storage(self):
        print('send signal', MyUserSignals.DEACTIVATE_DATA_STORING.name, 'to', self._target_pid)
        self.send_user_signal(self._target_pid, MyUserSignals.DEACTIVATE_DATA_STORING.value)

    def send_standard_signal(self, pid: int, signal: int):
        print(f'send_standard_signal({pid}, {signal})')
        super().send_standard_signal(pid, signal)

    def _stop_all(self):
        print('stop all')
        self.send_standard_signal(self._target_pid, signal.SIGTERM)
        time.sleep(0.1)
        self._root.destroy()

    def add_processor(self, name: str):
        processor = GuiProcessor(name, self._root)
        label = processor.get_label()
        label.grid(row=3, column=self._last_column, padx=self.padx, pady=self.pady)
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
processors_names = ['ACQUISITION 1', 'ACQUISITION 2', 'STORAGE 1', 'STORAGE 2']


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

    def _after_body(self):
        super()._after_body()
        self.logger().debug(f'{self.name()} ends')


class ExampleRunner(ProcessorsRunner, UserSignalConsumerProcessor):
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

        self.logger().info(f'+ START ({self.__class__.__name__}, PID={os.getpid()})')

        # Shared events for all processors
        self._acquisition_is_waiting_event = multiprocessing.Event()
        self._storage_is_waiting_event = multiprocessing.Event()

        ProcessorsRunner.__init__(
            self,
            name=name,
            multitasking_type=ConcurrencyType.PROCESSES,
            workers=[
                logger_processor,
                ProcessorsRunner(
                    name='ACQUISITIONS',
                    multitasking_type=ConcurrencyType.THREADS,
                    workers=[
                        LoopProcessorShowStateInFile(name=processors_names[0],
                                                     is_waiting_event=self._acquisition_is_waiting_event),
                        LoopProcessorShowStateInFile(name=processors_names[1],
                                                     is_waiting_event=self._acquisition_is_waiting_event)
                    ]
                ),
                ProcessorsRunner(
                    name='STORAGES',
                    multitasking_type=ConcurrencyType.THREADS,
                    workers=[
                        LoopProcessorShowStateInFile(name=processors_names[2],
                                                     is_waiting_event=self._storage_is_waiting_event),
                        LoopProcessorShowStateInFile(name=processors_names[3],
                                                     is_waiting_event=self._storage_is_waiting_event)
                    ],
                ),
            ],
            *args,
            **kwargs
        )
        UserSignalConsumerProcessor.__init__(self, signal_context=MySignalContext(), *args, **kwargs)

    def on_user_signal(self, user_signal_id: int, frame: types.FrameType,
                       common_signal_id: int = SignalContext.COMMON_SIGNAL):
        self.logger().info(
            f'{self.name()} user signal received: {user_signal_id} {MyUserSignals(user_signal_id).name},'
            f' common_signal_id: {common_signal_id}'
        )
        print(f'{self.name()} user signal received: {user_signal_id} {MyUserSignals(user_signal_id).name},'
              f' common_signal_id: {common_signal_id}')
        if user_signal_id == MyUserSignals.ACTIVATE_DATA_READING.value:
            self._acquisition_is_waiting_event.clear()
        if user_signal_id == MyUserSignals.DEACTIVATE_DATA_READING.value:
            self._acquisition_is_waiting_event.set()
        if user_signal_id == MyUserSignals.ACTIVATE_DATA_STORING.value:
            self._storage_is_waiting_event.clear()
        if user_signal_id == MyUserSignals.DEACTIVATE_DATA_STORING.value:
            self._storage_is_waiting_event.set()


# --- Running processes and GUI ----------------------------------------------------------------------------------------

def target_process():
    runner = ExampleRunner(
        name='ExampleRunner',
        logging_level=logging.DEBUG,
        stop_event=multiprocessing.Event()  # main stop event, which stops all processors
    )
    runner.run()


def gui_process(pid):
    """
    A GUI that uses buttons to simulate sending signals from an independent process (potentially,
    for example, from the command line).
    """
    gui = Gui(target_pid=pid, signal_context=MySignalContext())
    for name in processors_names:
        gui.add_processor(name)
    gui.run()


if __name__ == '__main__':
    p1 = multiprocessing.Process(target=target_process)
    p1.start()
    pid = p1.pid

    print('PID:', pid)

    p2 = multiprocessing.Process(target=gui_process, args=(pid,))
    p2.start()

    p2.join()
    p1.join()
