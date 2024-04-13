import logging
import os
import sys


debug = logging.debug
info = logging.info
warn = logging.warn
error = logging.error
fatal = logging.fatal


def severity(level):

    return {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warn": logging.WARN,
        "error": logging.ERROR,
        "fatal": logging.FATAL,
    }.get(level, logging.INFO)


def make_logger(severity, name):

    logger = logging.getLogger(name)
    logger.setLevel(severity)

    handler = logging.StreamHandler()
    handler.setLevel(severity)
    logger.addHandler(handler)

    if stream_supports_colour(handler.stream):
        formatter = StreamFormatter()
    else:
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{")
    handler.setFormatter(formatter)

    return logger, handler, formatter


class StreamFormatter(logging.Formatter):

    LEVEL_COLOURS = [
        (logging.DEBUG, "\x1b[38;5;183m"),
        (logging.INFO, "\x1b[38;5;45m"),
        (logging.WARNING, "\x1b[38;5;221m"),
        (logging.ERROR, "\x1b[38;5;203m"),
        (logging.CRITICAL, "\x1b[38;5;160m"),
    ]

    FORMATS = {
        level: logging.Formatter(
            f"\x1b[38;5;8m%(asctime)s\x1b[0m {colour}%(levelname)-8s\x1b[0m \x1b[38;5;15m%(name)s\x1b[0m %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f"\x1b[38;5;160m{text}\x1b[0m"

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output


def stream_supports_colour(stream) -> bool:

    is_a_tty = hasattr(stream, "isatty") and stream.isatty()

    if "PYCHARM_HOSTED" in os.environ:
        return is_a_tty

    if os.environ.get("TERM_PROGRAM") == "vscode":
        return is_a_tty

    if sys.platform != "win32":
        return is_a_tty

    return is_a_tty and ("ANSICON" in os.environ or "WT_SESSION" in os.environ)
