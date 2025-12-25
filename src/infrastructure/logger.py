"""日志系统。"""

import logging
import sys
from pathlib import Path


class Logger:
    """日志管理器。"""

    _instance: logging.Logger | None = None
    _initialized = False

    @classmethod
    def get_logger(cls, name: str = "ui-agent") -> logging.Logger:
        """获取日志记录器。

        Args:
            name: 日志记录器名称

        Returns:
            日志记录器实例
        """
        if cls._instance is None:
            cls._instance = logging.getLogger(name)
            cls._setup_logger(cls._instance)
            cls._initialized = True

        return cls._instance

    @classmethod
    def _setup_logger(cls, logger: logging.Logger) -> None:
        """设置日志记录器。

        Args:
            logger: 日志记录器
        """
        logger.setLevel(logging.DEBUG)

        # 清除现有的处理器
        logger.handlers.clear()

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # 文件处理器
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "ide_controller.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # 格式化器
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    @classmethod
    def set_level(cls, level: str) -> None:
        """设置日志级别。

        Args:
            level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        logger = cls.get_logger()
        logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        for handler in logger.handlers:
            handler.setLevel(getattr(logging, level.upper(), logging.INFO))
