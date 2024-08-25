#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    State indicator (for loop processors) in a file.
'''

import os

from git_root_to_syspath import agr; PROJECT_ROOT = agr()
NOGIT_DATA = os.path.join(PROJECT_ROOT, 'nogit_data')


class StateInFile:
    """
    Manages state passing between processes using files.
    """

    _ROOT_DIR = os.path.join(NOGIT_DATA, 'STATES')
    _initialized = False

    @staticmethod
    def init():
        """
        Initialize the directory for storing state files if not already initialized.
        """
        if not StateInFile._initialized:
            os.makedirs(StateInFile._ROOT_DIR, exist_ok=True)
            StateInFile._initialized = True

    @staticmethod
    def _get_file_name(name: str) -> str:
        """
        Generate a valid file name for the given state name.
        """
        return f'{name.replace(" ", "_")}.state'

    @classmethod
    def _get_path(cls, name: str) -> str:
        """
        Get the full path for the state file based on the state name.
        """
        return os.path.join(cls._ROOT_DIR, StateInFile._get_file_name(name))

    @staticmethod
    def _write_state_raw(path: str, state: str):
        """
        Write the raw state to the specified file.
        """
        StateInFile.init()
        with open(path, 'w') as file:
            file.write(state)

    @staticmethod
    def _write_state(name: str, is_active: bool):
        """
        Write the state (active or waiting) to the file based on the state name.
        """
        state = 'active' if is_active else 'waiting'
        path = StateInFile._get_path(name)
        StateInFile._write_state_raw(path, state)

    @staticmethod
    def read_state(name: str, default: str = 'waiting') -> str:
        """
        Read the state from the file. If the file does not exist, write the default state and return it.
        """
        path = StateInFile._get_path(name)
        if os.path.exists(path):
            with open(path, 'r') as file:
                state = file.read().strip()
                return state
        else:
            StateInFile._write_state_raw(path, default)
            return default
