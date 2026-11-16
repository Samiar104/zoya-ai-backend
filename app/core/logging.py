"""Logging setup for ZOYA AI Backend.

Logs go to stdout (for systemd/Docker) and to a rotating file
``logs/zoya.log`` (1 MB x 5 backups). Format is one line per event with
timestamp, level, logger and message.
"""
import logging
import logging.handlers
import sys
from pathlib import Path

_CONFIGURED = False


def get_logger(name: str = "zoya") -> logging.Logger:
    return logging.getLogger(name)


def setup_logging(level: str = "INFO") -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    numeric = getattr(logging, level.upper(), logging.INFO)
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    root = logging.getLogger()
    root.setLevel(numeric)
    root.handlers.clear()

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    root.addHandler(console)

    try:
        log_dir = Path(__file__).resolve().parents[2] / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_dir / "zoya.log", maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        fh.setFormatter(formatter)
        root.addHandler(fh)
    except OSError:
        # File logging is best-effort; stdout logging still works.
        pass

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
