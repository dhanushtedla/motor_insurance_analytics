"""Logging setup for the motor insurance project.

Logs go to logs/pipeline.log and to the console.
Never log passwords, AWS keys or personal customer details here.
"""
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = PROJECT_ROOT / "logs" / "pipeline.log"
LOGGER_NAME = "motor_insurance"


def setup_logger(name=LOGGER_NAME, log_file=LOG_FILE):
    """Create (or return) the project logger that writes to a file and the console."""
    logger = logging.getLogger(name)
    if logger.handlers:                      # already set up -> do not add handlers twice
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    try:                                     # file logging may fail on a read-only disk
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        logger.warning("Could not open log file, logging to console only.")
    return logger


def log_pipeline_step(message):
    """Write an INFO message (a normal pipeline step) to the log."""
    setup_logger().info(message)


def log_error(message):
    """Write an ERROR message to the log."""
    setup_logger().error(message)
