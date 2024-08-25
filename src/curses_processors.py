#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Terminates when defined keys are pressed.
'''

import multiprocessing
import curses
from time import sleep
from typing import Callable

# Root of project repository
from git_root_to_syspath import agr; PROJECT_ROOT = agr()

from src.loop_processor import LoopProcessor
from src.shared_values.multiproc_value import MultiprocessingValue, LabeledMultiprocValue


class CursesProcessor(LoopProcessor):
    """
    Initializes and terminates the curses environment.
    """
    def __init__(self, init_messages: '[str|(int, int, str)]' = [], *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not isinstance(init_messages, list):
            init_messages = [init_messages]

        self._init_messages = []
        for row, msg in enumerate(init_messages):
            self._init_messages.append(self._expand_message(row=row, complex_msg=msg))
        self._colors_pairs = {}
        self._stdscr = None

    def _expand_message(self, row, complex_msg, default_background=curses.COLOR_BLACK, default_foreground=curses.COLOR_WHITE):
        if isinstance(complex_msg, str):
            return row, 0, default_foreground, default_background, complex_msg
        l = len(complex_msg)
        if l == 3:
            foreground, background, msg = complex_msg
            return row, 0, foreground, background, msg
        elif l == 5:
            return complex_msg
        else:
            raise ValueError(f'Unexpected message format: msg="{complex_msg}" (type={type(complex_msg)}, len={l})')

    def _use_color(self, foreground, background) -> int:
        try:
            color_pair_id = self._colors_pairs[(foreground, background)]
        except KeyError:
            color_pair_id = len(self._colors_pairs) + 1
            curses.init_pair(color_pair_id, foreground, background)
            self._colors_pairs[(foreground, background)] = color_pair_id
        return color_pair_id

    def _add_msg(self, complex_msg):
        try:
            row, col, foreground, background, msg = complex_msg
            self._stdscr.addstr(row, col, self._add_nl(msg), self._use_color(foreground, background))
        except ValueError:
            try:
                foreground, background, msg = complex_msg
                self._stdscr.attron(self._use_color(foreground, background))
                self._stdscr.addstr(self._add_nl(msg))
            except ValueError:
                msg = complex_msg
                self._stdscr.addstr(self._add_nl(msg))

    def _add_nl(self, msg: str) -> str:
        msg = str(msg)
        if not msg.endswith('\n'):
            msg += '\n'
        return msg

    def show(self):
        for complex_message in self._init_messages:
            self._add_msg(complex_message)

    def _before_body(self):
        try:
            self._stdscr = curses.initscr()
            curses.noecho()
            curses.cbreak()
            self._stdscr.keypad(True)
            curses.start_color()
            sleep(0.5)
            self.show()
            self._stdscr.refresh()
        except Exception as e:
            self.logger().error(e)

    def _after_body(self):
        curses.nocbreak()
        self._stdscr.keypad(False)
        curses.echo()
        curses.endwin()


class ActionsKeyCursesProcessor(CursesProcessor):
    """
    Processes key actions based on defined characters.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._actions = {}

    def add_action(self, chars: str, action: Callable):
        self._actions[chars] = action

    def _before_body(self):
        super(ActionsKeyCursesProcessor, self)._before_body()
        self._stdscr.timeout(0)  # no delay

    def _work_in_loop(self):
        try:
            key = self._stdscr.getkey()
        except curses.error:
            return
        for chars, action in self._actions.items():
            if key in chars:
                action()
                break


class StopKeypressedProcessor(ActionsKeyCursesProcessor):
    """
    Executes an action when a defined key is pressed.
    """
    def __init__(self, sleep_s: float = 0.1, init_messages: '[str|(int, int, str)]' = [], *args, **kwargs):
        quit_chars = 'qQ' + chr(27)
        init_messages.append((curses.COLOR_CYAN, curses.COLOR_BLACK, f'Press one of these keys "{quit_chars}" to exit.\n'))
        super().__init__(init_messages=init_messages, *args, **kwargs)
        self.add_action(chars=quit_chars, action=self.set_stop_event_to_stop)
        self._sleep_s = sleep_s

    def _work_in_loop(self):
        super(StopKeypressedProcessor, self)._work_in_loop()
        sleep(self._sleep_s)


class StopKeypressedProcessorWithValue(StopKeypressedProcessor):
    """
    Monitors shared values and updates the display when they change.
    """
    def __init__(self, monitored_variables: [LabeledMultiprocValue], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._monitored_variables = monitored_variables
        self._start_row = len(self._init_messages) + 2
        self._first_call = True

    def _work_in_loop(self):
        self.show()
        super()._work_in_loop()

    def show(self):
        messages = []
        for i, shared_value in enumerate(self._monitored_variables):
            if (abs(shared_value.value - shared_value.last_value) >= shared_value.threshold) or self._first_call:
                row = self._start_row + i
                actual_value_formatted = f'{shared_value.value:,}'.replace(',', ' ')
                messages.append((row, 0, curses.COLOR_GREEN, curses.COLOR_BLACK, f'{shared_value.label}: {actual_value_formatted}' + '      '))
                shared_value.last_value = shared_value.value

        self._first_call = False
        if messages:
            super().show()
            for msg in messages:
                self._add_msg(msg)
            self._stdscr.refresh()


if __name__ == '__main__':
    """
    Must be run in terminal.
    """
    shared_value = MultiprocessingValue(value=1)
    labeled_shared_values = LabeledMultiprocValue(shared_value=shared_value.wrapper, label='Count of messages', threshold=1)

    stop_event = multiprocessing.Event()

    def fake_sender(shared_value: MultiprocessingValue, stop_event: multiprocessing.Event):
        for i in range(20):
            sleep(0.2)
            shared_value.value += 1
            if stop_event.is_set():
                break
        stop_event.set()

    def viewer(labeled_shared_values: LabeledMultiprocValue, stop_event: multiprocessing.Event):
        s = StopKeypressedProcessorWithValue(stop_event=stop_event, monitored_variables=[labeled_shared_values])
        s.run()

    p1 = multiprocessing.Process(target=fake_sender, args=(labeled_shared_values, stop_event,))
    p2 = multiprocessing.Process(target=viewer, args=(labeled_shared_values, stop_event,))
    p1.start()
    p2.start()
    p1.join()
    p2.join()
