import configparser
import os


class NoValue:
    pass


class BlankDefault:
    pass


CONFIG = configparser.ConfigParser()

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
        "keep_relative_path": True,
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


def get(*args, default=BlankDefault(), return_type=None):
    CONFIG.read('./config.ini')
    value = CONFIG.get(*args, fallback=deep_get(args))

    found = None
    if isinstance(value, NoValue):
        if isinstance(default, BlankDefault):
            import rowdo.logging
            err = KeyError(f'Desired setting is not found in ./config.ini: { " -> ".join(args) }')
            rowdo.logging.logger.error(err)
            raise err
        else:
            found = default
    else:
        found = value

    if return_type == list:
        found_whitespaced_list = found.split(',')
        found = []
        for item in found_whitespaced_list:
            found.append(item.strip())

    return found
