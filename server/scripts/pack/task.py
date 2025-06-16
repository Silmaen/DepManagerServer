"""
Simple long task manager.
"""

from .db_repair import long_repair
from .db_import import long_import


def database_repair():
    """

    :return:
    """
    from .logger import logger

    def async_repair():
        """

        :return:
        """
        from .db_locking import locker

        if not locker.get_lock():
            logger.warning("Cannot launch async database repair: cannot get the lock.")
            return
        try:
            logger.info("Database lock acquired for database repair.")
            long_repair(do_correct=True, skip_large_files=False)
        except Exception as err_ar:
            logger.error(f"Exception during database repair: {err_ar}")
        finally:
            locker.release_lock()
            logger.info("Database lock released.")

    logger.info(f"database_repair: Starting.")
    use_thread = False
    if use_thread:
        from threading import Thread

        try:
            long_running_thread = Thread(target=async_repair)
            long_running_thread.start()
        except Exception as err:
            logger.error(f"Exception while database repair invocation: {err}.")
    else:
        from multiprocessing import Process

        long_running_process = Process(target=async_repair)
        long_running_process.start()
    logger.info(f"Continue view execution")


def database_import(url: str, user: str, password: str):
    """
    Meta function to import data from another server.
    :return:
    """
    from .logger import logger

    def async_repair():
        """

        :return:
        """
        from .db_locking import locker

        if not locker.get_lock():
            logger.warning(
                f"Cannot launch async database import from {url}: cannot get the lock."
            )
            return
        try:
            logger.info(f"Database lock acquired for import from {url}.")
            long_import(url=url, user=user, password=password)
        except Exception as err_ar:
            logger.error(f"Exception during database import from {url}: {err_ar}")
        finally:
            locker.release_lock()
            logger.info("Database lock released.")

    logger.info(f"import from {url}: Starting.")
    use_thread = False
    if use_thread:
        from threading import Thread

        try:
            long_running_thread = Thread(target=async_repair)
            long_running_thread.start()
        except Exception as err:
            logger.error(
                f"Exception while database import from {url} invocation: {err}."
            )
    else:
        from multiprocessing import Process

        long_running_process = Process(target=async_repair)
        long_running_process.start()
    logger.info(f"Continue view execution")
