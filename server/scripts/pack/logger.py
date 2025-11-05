"""
Loging system
"""

import logging


class Logger:
    """
    Simple logging class.
    """

    def __init__(self):
        self._django_logger = logging.getLogger("pack")

    def fatal(self, message: str):
        """
        Log message with FATAL severity
        :param message: Message to log.
        """
        self._django_logger.fatal(message)

    def error(self, message: str):
        """
        Log message with ERROR severity
        :param message: Message to log.
        """
        self._django_logger.error(message)

    def warning(self, message: str):
        """
        Log message with WARNING severity
        :param message: Message to log.
        """
        self._django_logger.warning(message)

    def info(self, message: str):
        """
        Log message with INFO severity
        :param message: Message to log.
        """
        self._django_logger.info(message)

    def debug(self, message: str):
        """
        Log message with INFO severity
        :param message: Message to log.
        """
        self._django_logger.debug(message)


logger = Logger()
