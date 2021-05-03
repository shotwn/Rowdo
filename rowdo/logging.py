import rowdo.config
from loguru import logger


def get_severity_name(severity):
    severities = {
        'CRITICAL': 50,
        'ERROR': 40,
        'WARNING': 30,
        'INFO': 20,
        'DEBUG': 10,
        'TRACE': 5,
        'NOTSET': 0
    }

    for key, val in severities.items():
        if val == severity:
            return key

    return severity


if rowdo.config.get('runtime', 'debug', default=False):
    logger.add("debug.log", backtrace=True, diagnose=True)  # Caution, may leak sensitive data in prod
