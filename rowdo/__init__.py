import os

import rowdo.database
import rowdo.watcher
import rowdo.config
from rowdo.logging import logger

WATCHER_INSTANCE = None


@logger.catch
def debug():
    run()


def run():
    global WATCHER_INSTANCE
    db = rowdo.database.Database()
    WATCHER_INSTANCE = rowdo.watcher.Watcher(db)
    # watcher.routine()
    WATCHER_INSTANCE.loop()


def start(working_directory=None):
    """Start rowdo loop

    Args:
        working_directory (str, optional): Change current working directory. Defaults to None.
    """
    if working_directory:
        os.chdir(os.path.dirname(working_directory))

    rowdo.logging.start_log_file()

    if rowdo.config.get('runtime', 'debug'):
        debug()
    else:
        run()


def stop():
    """Stop rowdo loop
    """
    WATCHER_INSTANCE.stop()
