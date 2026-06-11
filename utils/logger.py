import logging

from settings import APP_DEBUG


def setup_logging() -> None:
    level = logging.DEBUG if APP_DEBUG else logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(levelname)s %(message)s"
    )