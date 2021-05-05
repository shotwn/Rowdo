import os
import sys

import rowdo.database
import rowdo.watcher
import rowdo.config
from rowdo.logging import logger, start_log_file

WATCHER_INSTANCE = None


@logger.catch
def debug():
    run()


def run():
    global WATCHER_INSTANCE

    try:
        db = rowdo.database.Database()
    except Exception as err:
        logger.error('Database initiation error. Check connection, confirm credentials in config.ini.')
        logger.debug(err)
        sys.exit('DB Error')

    WATCHER_INSTANCE = rowdo.watcher.Watcher(db)
    # watcher.routine()
    WATCHER_INSTANCE.loop()


def start(working_directory=None):
    """Start rowdo loop

    Args:
        working_directory (str, optional): Change current working directory if config.runtime.working_directory does not exist. Defaults to None.
    """
    working_directory_override = rowdo.config.get('runtime', 'working_directory')
    if working_directory_override:
        os.chdir(os.path.join(working_directory_override))
    elif working_directory:  # Called by sys.argv[0] real cwd in service mode.
        os.chdir(os.path.dirname(working_directory))

    start_log_file()

    if rowdo.config.get('runtime', 'debug'):
        debug()
    else:
        run()


def stop():
    """Stop rowdo loop
    """
    WATCHER_INSTANCE.stop()
