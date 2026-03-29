import logging
import sys


def setup_logging(level: str = "INFO"):
    """
    Configure root logger for the project.
    """
    logger = logging.getLogger("ezmig")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(getattr(logging, level.upper(), logging.INFO))
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger
