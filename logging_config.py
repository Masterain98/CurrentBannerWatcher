import logging
import os

from colorama import init


VALID_LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
}


def configure_logging(level_name: str | None = None) -> None:
    init(autoreset=True)
    configured_level = level_name or os.getenv("LOG_LEVEL")
    if configured_level is None:
        configured_level = "debug" if os.getenv("run_mode") == "debug" else "info"

    normalized_level = configured_level.lower()
    if normalized_level not in VALID_LOG_LEVELS:
        choices = ", ".join(VALID_LOG_LEVELS)
        raise ValueError(f"Invalid LOG_LEVEL {configured_level!r}; expected one of: {choices}")

    logging.basicConfig(
        level=VALID_LOG_LEVELS[normalized_level],
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
