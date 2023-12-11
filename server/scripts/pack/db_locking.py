"""
Simple locking system for the database
"""
from datetime import datetime
from pathlib import Path

from scripts.settings import DATABASES_LOCK_PATH


class DbLocking:
    """
    Simple lock file management.
    """

    def __init__(self):
        self.lockfile = Path(DATABASES_LOCK_PATH).resolve()
        if not self.lockfile.parent.exists():
            self.lockfile.parent.mkdir(parents=True)
        self.lock_timeout = 300

    def is_locked(self):
        """
        Check if the database is locked.
        Remove the lock is the lock file is older thant the timeout.
        :return: True if lock file exists and valid.
        """
        if self.lockfile.exists():
            if (
                datetime.fromtimestamp(self.lockfile.stat().st_mtime) - datetime.now()
            ).total_seconds() > self.lock_timeout:
                self.lockfile.unlink()
                return False
            return True
        return False

    def get_lock(self):
        """
        Try to lock the database if not already lock
        :return: True if the lock is given, False if the database is already locked.
        """
        if self.is_locked():
            return False
        self.lockfile.touch()
        return True

    def release_lock(self):
        """
        Release the lock.
        """
        if self.lockfile.exists():
            self.lockfile.unlink()


locker = DbLocking()
