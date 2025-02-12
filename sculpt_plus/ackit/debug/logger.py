import logging
import datetime
from pathlib import Path
from typing import Optional, Union

from ..globals import GLOBALS


class AddonLogger:
    """
    Logger utility for Blender addons that handles both console and file logging.
    Automatically creates logs in the addon's config directory.
    """
    _instances = {}  # Store logger instances per addon

    def __init__(self, name: str, log_level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)

        if not self.logger.handlers:
            self._setup_handlers()

    @classmethod
    def get_logger(cls, addon_name: Optional[str] = None) -> 'AddonLogger':
        """Get or create a logger instance for the specified addon."""
        name = addon_name or GLOBALS.ADDON_MODULE
        if name not in cls._instances:
            cls._instances[name] = cls(name)
        return cls._instances[name]

    def _setup_handlers(self):
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(name)s - %(levelname)s: %(message)s')
        )
        self.logger.addHandler(console_handler)

        # File handler
        log_file = self._get_log_file_path()
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s: %(message)s')
        )
        self.logger.addHandler(file_handler)

    def _get_log_file_path(self) -> Path:
        """Create and return the path for the log file."""
        config_dir = Path(GLOBALS.USER_CONFIG_DIR)
        logs_dir = config_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        return logs_dir / f"{GLOBALS.ADDON_MODULE}_{timestamp}.log"

    def debug(self, msg: str, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        self.logger.exception(msg, *args, **kwargs)


# Convenience function to get logger
def get_logger(addon_name: Optional[str] = None) -> AddonLogger:
    return AddonLogger.get_logger(addon_name)
