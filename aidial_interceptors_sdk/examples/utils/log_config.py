import logging
import os
import sys

from uvicorn.logging import DefaultFormatter

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


def configure_loggers():
    # Making the uvicorn logger delegate logging to the root logger
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_logger.handlers = []
    uvicorn_logger.propagate = True

    # Setting up log levels
    for name in ["aidial_interceptors_sdk", "uvicorn"]:
        logging.getLogger(name).setLevel(LOG_LEVEL)

    # Configuring the root logger
    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    root_has_stderr_handler = any(
        isinstance(handler, logging.StreamHandler)
        and handler.stream == sys.stderr
        for handler in root.handlers
    )

    # If stderr handler is already set, then no need to add another one
    if not root_has_stderr_handler:
        formatter = DefaultFormatter(
            fmt="%(levelprefix)s | %(asctime)s | %(name)s | %(process)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            use_colors=True,
        )

        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
        root.addHandler(handler)
