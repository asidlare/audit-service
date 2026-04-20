import logging
import sys


def setup_logger(name: str = "AuditApp") -> logging.Logger:
    """
    Sets up a logger with the specified name and standard configurations. If a logger
    with the given name already exists and has handlers, the existing logger will
    be returned without adding new handlers. Otherwise, a new logger will be
    configured to write logs to the console with a predefined format.

    This function ensures consistent logging formatting and prevents the addition
    of duplicate handlers during multiple invocations.

    :param name: The name of the logger to be created or retrieved, defaults to "AuditApp".
    :type name: str
    :return: A configured logger instance.
    :rtype: logging.Logger
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    return logger


# Default logger instance
logger = setup_logger()
