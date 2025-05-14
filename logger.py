"""Dags logger."""
import os
import logging
import sys

# Usage: loglevel=0 (none), loglevel=1 (info), loglevel=2 (debug)
all_levels = {0: logging.NOTSET, 1: logging.INFO, 2: logging.DEBUG}


class CustomFormatter(logging.Formatter):
    """Custom formatting for the logger."""

    yellow = "\x1b[33;20m"
    green = "\x1b[32;20m"
    cyan = "\x1b[36;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    pre = "[%(asctime)s-%(name)s-%(levelname)s]"
    post = "(%(filename)s:%(funcName)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: f"{cyan}{pre}{reset} %(message)s {yellow}{post}{reset}",
        logging.INFO: f"{green}{pre}{reset} %(message)s {yellow}{post}{reset}",
        logging.WARNING: f"{yellow}{pre}{reset} %(message)s {yellow}{post}{reset}",
        logging.ERROR: f"{red}{pre}{reset} %(message)s {yellow}{post}{reset}",
        logging.CRITICAL: f"{bold_red}{pre}{reset} %(message)s {yellow}{post}{reset}",
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        formatter.formatTime = self.formatTime
        return formatter.format(record)

    def formatTime(self, record, datefmt=None):
        return super().formatTime(record, "%Y%m%d %H:%M:%S")


def build_logger(key: str) -> logging.Logger:
    """Returns a custom logger with the specified key."""
    # instantiate logger and set log level
    logger = logging.getLogger(key)
    # default log level is INFO, change it via the env variable
    log_level = int(os.environ.get(f"{key}_LOGLEVEL", 2))
    logger.setLevel(all_levels[log_level])
    # add custom formatter to logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CustomFormatter())
    logger.addHandler(handler)
    return logger


# exported module logger
dags_logger = build_logger("DAGS")
