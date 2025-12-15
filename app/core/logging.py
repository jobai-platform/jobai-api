import logging
import sys


class CustomFormatter(logging.Formatter):
    """
    A custom formatter for logging that adds specific formatting to log messages.
    """
    grey = "\x1b[38;20m"
    blue = "\x1b[34;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: blue + format_string + reset,
        logging.INFO: grey + format_string + reset,
        logging.WARNING: yellow + format_string + reset,
        logging.ERROR: red + format_string + reset,
        logging.CRITICAL: bold_red + format_string + reset,
    }


    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.format_string)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logging(disable_sqlalchemy: bool = True) -> None:
    """
    Set up logging configuration with custom formatter.
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(CustomFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = []
    root_logger.addHandler(handler)

    if disable_sqlalchemy:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.CRITICAL)
        logging.getLogger("sqlalchemy.engine.base.Engine").disabled = True
        logging.getLogger("sqlalchemy.dialects").setLevel(logging.CRITICAL)
        logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)
        logging.getLogger("sqlalchemy.orm").setLevel(logging.CRITICAL)

    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)

