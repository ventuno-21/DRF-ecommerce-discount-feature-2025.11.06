import logging
from logging.handlers import RotatingFileHandler
import os
import colorlog

LOG_DIR = "logs"
LOG_FILE = "app.log"

os.makedirs(LOG_DIR, exist_ok=True)

# color details
color_formatter = colorlog.ColoredFormatter(
    "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    log_colors={
        "DEBUG": "cyan",
        "INFO": "green",
        "WARNING": "yellow",
        "ERROR": "red",
        "CRITICAL": "bold_red,bg_white",
    },
)

file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("my_app_logger")
logger.setLevel(logging.DEBUG)

# console handler with color
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(color_formatter)

# file handler without color
file_handler = RotatingFileHandler(
    os.path.join(LOG_DIR, LOG_FILE), maxBytes=5 * 1024 * 1024, backupCount=3
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(file_formatter)

# adding handlers
logger.addHandler(console_handler)
logger.addHandler(file_handler)
