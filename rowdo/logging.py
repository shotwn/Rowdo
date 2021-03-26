import rowdo.config
from loguru import logger


if rowdo.config.get('runtime', 'debug', default=False):
    logger.add("debug.log", backtrace=True, diagnose=True)  # Caution, may leak sensitive data in prod
