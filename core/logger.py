import logging
import sys
from datetime import datetime

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger for a module."""
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)

        # Console handler — shows INFO and above
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S"
        ))

        # File handler — saves everything to logs/pipeline.log
        import os
        os.makedirs("logs", exist_ok=True)
        file_handler = logging.FileHandler(
            f"logs/pipeline_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        ))

        logger.addHandler(console)
        logger.addHandler(file_handler)

    return logger