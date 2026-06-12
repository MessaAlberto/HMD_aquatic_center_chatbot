import logging
import warnings

from utils.settings import APP_DEBUG


def setup_logging() -> None:
    warnings.filterwarnings("ignore", category=FutureWarning)

    level = logging.DEBUG if APP_DEBUG else logging.WARNING

    logging.basicConfig(
        level=level,
        format="%(levelname)s %(message)s",
        force=True,
    )