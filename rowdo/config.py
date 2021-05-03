import configparser
import os


class NoValue:
    pass


class BlankDefault:
    pass


CONFIG = configparser.ConfigParser()
CONFIG.read('./config.ini')

DEFAULTS = {
    "runtime": {
        "debug": False,
        "run_every_seconds": 10
    },
    "database": {
        "table_prefix": "rowdo",
        "url": False
    },
    "download": {
        "disallow_from": "",
        "allow_from": "*",
        "allow_formats_url": "*",
        "enabled": True,
        "path": os.path.join('files'),
        "keep_relative_path": False,
        "allow_mime_types": "*",
        "max_attempts": 3
    }
}


def deep_get(levels):
    no_val = NoValue()
    out = DEFAULTS

    for level in levels:
        if out is not no_val:
            out = out.get(level, no_val)
        else:
            break

    return out


def get(*args, default=BlankDefault()):
    value = CONFIG.get(*args, fallback=deep_get(args))

    if isinstance(value, NoValue):
        if isinstance(default, BlankDefault):
            raise KeyError(f'Desired setting is not found in ../config.ini: { " -> ".join(args) }')
        else:
            return default

    return value
