"""
Loging system
"""
from datetime import datetime
from pathlib import Path
from sys import stderr

from scripts.settings import PACKAGE_LOGING

levels = [
    "SILENT",  # 0
    "FATAL",  # 1
    "ERROR",  # 2
    "WARNING",  # 3
    "INFO",  # 4
    "DEBUG",  # 5
    "TRACE",  # 6
]


class Logger:
    """
    Simple logging class.
    """

    def __init__(self):
        self.level = 3
        self.console = False
        self.file = Path()
        if "level" in PACKAGE_LOGING:
            self.set_level(PACKAGE_LOGING["level"])
        if "console" in PACKAGE_LOGING:
            if type(PACKAGE_LOGING["console"]) == bool:
                self.console = PACKAGE_LOGING["console"]
        if "file" in PACKAGE_LOGING:
            self.file = Path(PACKAGE_LOGING["file"]).resolve()
            if self.file.parent == self.file:
                self.file = Path()
                return
            if not self.file.parent.exists():
                self.file.parent.mkdir(parents=True)
                if not self.file.parent.exists():
                    self.file = Path()
                    return

    def set_level(self, new_level: any([int, str]) = 3):
        """
        Define the new verbosity level
        :param new_level: New verbosity level.
        """
        if type(new_level) == int:
            self.level = min(max(new_level, 0), 6)
        elif type(new_level) == str:
            if new_level.upper() in levels:
                self.level = levels.index(new_level.upper())

    def fatal(self, message: str):
        """
        Log message with FATAL severity
        :param message: Message to log.
        """
        self.__print(message, 1)

    def error(self, message: str):
        """
        Log message with ERROR severity
        :param message: Message to log.
        """
        self.__print(message, 2)

    def warning(self, message: str):
        """
        Log message with WARNING severity
        :param message: Message to log.
        """
        self.__print(message)

    def info(self, message: str):
        """
        Log message with INFO severity
        :param message: Message to log.
        """
        self.__print(message, 4)

    def debug(self, message: str):
        """
        Log message with INFO severity
        :param message: Message to log.
        """
        self.__print(message, 5)

    def trace(self, message: str):
        """
        Log message with INFO severity
        :param message: Message to log.
        """
        self.__print(message, 6)

    def __print(self, message: str, level: int = 3):
        if level > self.level:
            return
        time = datetime.now()
        date = f"{time.year:04d}/{time.month:02d}/{time.day:02d} {time.hour:02d}:{time.minute:02d}:{time.second:02d}"
        lev_str = f"[{levels[level].lower()}]"
        prefix = f"{date} {lev_str}"
        if self.console:
            print(f"{prefix} {message}", file=stderr, flush=True)
        if self.file != Path():
            with open(self.file, "a") as fp:
                print(f"{prefix} {message}", file=fp, flush=True)


logger = Logger()
