import rowdo.config
import rowdo.database
import rowdo.watcher
from rowdo.logging import logger


@logger.catch
def debug():
    run()


def run():
    db = rowdo.database.Database()
    watcher = rowdo.watcher.Watcher(db)
    # watcher.routine()
    watcher.loop()


if __name__ == "__main__":
    if rowdo.config.get('runtime', 'debug'):
        debug()
    else:
        run()
