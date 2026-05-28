import logging
import sys
from datetime import datetime
from pathlib import Path

from colorama import Fore, Style, init as colorama_init

colorama_init(autoreset=True)


LEVEL_STYLE = {
    "DEBUG":    (Fore.LIGHTBLACK_EX, "DBG"),
    "INFO":     (Fore.CYAN,          "INF"),
    "SUCCESS":  (Fore.LIGHTGREEN_EX, "OK "),
    "WARNING":  (Fore.YELLOW,        "WRN"),
    "ERROR":    (Fore.LIGHTRED_EX,   "ERR"),
    "CRITICAL": (Fore.MAGENTA,       "CRT"),
}

SUCCESS_LEVEL = 25
logging.addLevelName(SUCCESS_LEVEL, "SUCCESS")


class _ColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        color, tag = LEVEL_STYLE.get(record.levelname, (Fore.WHITE, record.levelname[:3]))
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        scope = getattr(record, "scope", record.name)
        prefix = (
            f"{Style.DIM}{Fore.WHITE}{ts}{Style.RESET_ALL} "
            f"{color}{Style.BRIGHT}[{tag}]{Style.RESET_ALL} "
            f"{Fore.LIGHTBLUE_EX}{scope:<16}{Style.RESET_ALL} "
            f"{Fore.LIGHTBLACK_EX}|{Style.RESET_ALL} "
        )
        message = record.getMessage()
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        return f"{prefix}{color}{message}{Style.RESET_ALL}"


class _PlainFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        scope = getattr(record, "scope", record.name)
        msg = record.getMessage()
        if record.exc_info:
            msg = f"{msg}\n{self.formatException(record.exc_info)}"
        return f"{ts} [{record.levelname:<7}] {scope:<16} | {msg}"


class ScopedLogger:
    def __init__(self, logger: logging.Logger, scope: str):
        self._logger = logger
        self._scope = scope

    def _log(self, level: int, msg: str, *args, exc_info=False):
        self._logger.log(level, msg, *args, exc_info=exc_info, extra={"scope": self._scope})

    def debug(self, msg: str, *args, **kw): self._log(logging.DEBUG, msg, *args, **kw)
    def info(self, msg: str, *args, **kw):  self._log(logging.INFO, msg, *args, **kw)
    def success(self, msg: str, *args, **kw): self._log(SUCCESS_LEVEL, msg, *args, **kw)
    def warning(self, msg: str, *args, **kw): self._log(logging.WARNING, msg, *args, **kw)
    def error(self, msg: str, *args, **kw): self._log(logging.ERROR, msg, *args, **kw)
    def critical(self, msg: str, *args, **kw): self._log(logging.CRITICAL, msg, *args, **kw)
    def exception(self, msg: str, *args):
        self._log(logging.ERROR, msg, *args, exc_info=True)


_BASE_LOGGER: logging.Logger | None = None


def setup_logging(log_dir: Path = Path("data/logs"), level: int = logging.INFO) -> None:
    global _BASE_LOGGER
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger("inviter")
    root.setLevel(level)
    root.handlers.clear()
    root.propagate = False

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(_ColorFormatter())
    stream.setLevel(level)
    root.addHandler(stream)

    file_handler = logging.FileHandler(
        log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(_PlainFormatter())
    file_handler.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    for noisy in ("pyrogram", "pyrogram.session", "pyrogram.connection", "pyrogram.dispatcher"):
        logging.getLogger(noisy).setLevel(logging.ERROR)

    _BASE_LOGGER = root


def get_logger(scope: str) -> ScopedLogger:
    if _BASE_LOGGER is None:
        setup_logging()
    assert _BASE_LOGGER is not None
    return ScopedLogger(_BASE_LOGGER, scope)
