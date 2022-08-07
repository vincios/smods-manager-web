import logging
from os.path import normpath, join, dirname

import smods_manager.app

LOGFILE = normpath(join(dirname(__file__), '..', "log.log"))

FILE_HANDLER, CONSOLE_HANDLER = logging.FileHandler(LOGFILE, "a+"), logging.StreamHandler()

CONFIG_LOGGING_LEVEL = "DEBUG" if smods_manager.app.DEBUG else "INFO"

DEFAULT_LOGGING_LEVEL = logging.getLevelName(CONFIG_LOGGING_LEVEL)


def get_logger(name, level=None, console=True):
    formats = {"console": '[%(levelname)5s] [%(filename)s:%(lineno)s %(funcName)s()]: \u001b[37m %(message)s\033[0m',
               "file": '[%(levelname)5s] [%(process)5d: %(filename)s:%(lineno)s %(funcName)s()]: %(message)s'}

    # if os.path.exists(logfile):
    #     os.remove(logfile)

    logger = logging.getLogger(name)
    level = level if level else DEFAULT_LOGGING_LEVEL
    logger.setLevel(level)

    if console:
        CONSOLE_HANDLER.setFormatter(logging.Formatter(formats["console"]))
        CONSOLE_HANDLER.setLevel(level)
        logger.addHandler(CONSOLE_HANDLER)

    FILE_HANDLER.setFormatter(logging.Formatter(formats["file"]))
    FILE_HANDLER.setLevel(level)

    logger.addHandler(FILE_HANDLER)

    return logger
