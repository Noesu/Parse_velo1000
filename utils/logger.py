import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging():
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                log_dir / "parser.log",
                maxBytes=5 * 1024 * 1024,
                backupCount=3,
                encoding='utf-8'
            ),
            logging.StreamHandler()
        ]
    )