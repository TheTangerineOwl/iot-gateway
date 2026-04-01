import logging
from sys import stdout
from typing import TextIO


def setup_logging(
        level: str = "INFO",
        format: str | None = None,
        dateformat: str | None = None,
        # handler: logging.StreamHandler = logging.StreamHandler(stdout)
        stream: TextIO = stdout
) -> None:
    # DEBUG, INFO, WARNING, ERROR
    log_level = getattr(logging, level.upper(), logging.INFO)

    formatter = logging.Formatter(
        fmt=format,
        datefmt=dateformat,
    )

    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
    logging.getLogger(__name__).info(
        f"Logging initialized at {level.upper()} level"
    )
