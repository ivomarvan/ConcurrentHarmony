#!/usr/bin/env python3
# -*- coding: utf-8 -*-
__author__ = "Ivo Marvan"
__email__ = "ivo@marvan.cz"
__description__ = '''
    Access to the logging object
'''

import logging


class LoggerAccess:
    """
    Access for default configured logger
    """
    _logger: logging.Logger = None

    @classmethod
    def logger(cls) -> logging.Logger:
        if cls._logger is None:
            cls._logger = logging.getLogger('app')
            if not cls._logger.handlers:
                # Fallback plan - use standard logging to stderr if no handlers are configured
                handler = logging.StreamHandler()
                cls._logger.addHandler(handler)
                cls._logger.info('Fallback plan - using standard logging to stderr.')
        return cls._logger

