import logging

from src.utils.enviroments import B2BEnvironments

def configure_logging() -> None:
    level_name = B2BEnvironments().LOG_LEVEL
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)