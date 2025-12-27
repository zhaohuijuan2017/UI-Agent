"""浏览器启动器模块。"""

import logging
import re
import webbrowser

from src.browser.exceptions import (
    BrowserLaunchError,
    BrowserNotFoundError,
    InvalidURLError,
)

logger = logging.getLogger(__name__)

# 浏览器名称到注册表名称的映射
BROWSER_MAP = {
    "chrome": "chrome",
    "edge": "msedge",
    "firefox": "firefox",
    "safari": "safari",
    "opera": "opera",
    "默认": None,
}

# URL 验证正则表达式
URL_PATTERN = re.compile(
    r"^(?:(?:https?|ftp)://)"  # 协议（必须）
    r"|(?:localhost|(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,})"  # 域名
    r"(?::\d+)?"  # 端口
    r"(?:/.*)?$",  # 路径
    re.IGNORECASE,
)


class BrowserLauncher:
    """跨平台浏览器启动器。"""

    def __init__(self) -> None:
        """初始化浏览器启动器。"""
        self._browser_map = self._build_browser_map()

    def _build_browser_map(self) -> dict[str, str | None]:
        """构建浏览器映射表。

        Returns:
            浏览器名称到注册表名称的映射
        """
        browser_map: dict[str, str | None] = {}

        # 检查每个浏览器是否可用
        for name, registration in BROWSER_MAP.items():
            if registration is None:
                # 默认浏览器总是可用
                browser_map[name] = registration
            elif self._is_browser_available(registration):
                browser_map[name] = registration
                logger.debug(f"浏览器可用: {name} -> {registration}")

        return browser_map

    def _is_browser_available(self, registration: str) -> bool:
        """检查浏览器是否可用。

        Args:
            registration: 浏览器注册表名称

        Returns:
            浏览器是否可用
        """
        try:
            # 尝试获取浏览器控制器
            controller = webbrowser.get(using=registration)
            return controller is not None
        except Exception:
            return False

    def validate_url(self, url: str) -> bool:
        """验证 URL 格式。

        Args:
            url: 待验证的 URL

        Returns:
            URL 是否有效
        """
        if not url:
            return False

        # 检查是否是有效的 URL 格式
        if not URL_PATTERN.match(url):
            return False

        return True

    def normalize_url(self, url: str) -> str:
        """标准化 URL。

        如果 URL 不包含协议，自动添加 https://。

        Args:
            url: 待标准化的 URL

        Returns:
            标准化后的 URL

        Raises:
            InvalidURLError: URL 格式无效
        """
        if not url:
            raise InvalidURLError("URL 不能为空")

        url = url.strip()

        # 如果没有协议前缀，自动添加 https://
        if not re.match(r"^[a-zA-Z]+://", url):
            # 检查是否是有效的域名或 localhost
            if URL_PATTERN.match(url):
                url = f"https://{url}"
            else:
                raise InvalidURLError(url)

        return url

    def open_default_browser(self, url: str) -> bool:
        """使用默认浏览器打开网址。

        Args:
            url: 目标网址

        Returns:
            是否成功打开

        Raises:
            InvalidURLError: URL 格式无效
            BrowserLaunchError: 浏览器启动失败
        """
        # 标准化 URL
        url = self.normalize_url(url)

        # 验证 URL
        if not self.validate_url(url):
            raise InvalidURLError(url)

        try:
            logger.info(f"使用默认浏览器打开: {url}")
            webbrowser.open(url)
            return True
        except Exception as e:
            raise BrowserLaunchError("默认浏览器", url, str(e))

    def open_browser(self, url: str, browser: str) -> bool:
        """使用指定浏览器打开网址。

        Args:
            url: 目标网址
            browser: 浏览器名称（chrome、edge、firefox 等）

        Returns:
            是否成功打开

        Raises:
            InvalidURLError: URL 格式无效
            BrowserNotFoundError: 浏览器未找到
            BrowserLaunchError: 浏览器启动失败
        """
        # 标准化 URL
        url = self.normalize_url(url)

        # 验证 URL
        if not self.validate_url(url):
            raise InvalidURLError(url)

        # 查找浏览器注册表名称
        browser_lower = browser.lower()
        if browser_lower not in self._browser_map:
            available = list(self._browser_map.keys())
            raise BrowserNotFoundError(browser, available)

        registration = self._browser_map[browser_lower]

        try:
            if registration is None:
                # 使用默认浏览器
                logger.info(f"使用默认浏览器打开: {url}")
                webbrowser.open(url)
            else:
                # 使用指定浏览器
                logger.info(f"使用 {browser} 浏览器打开: {url}")
                controller = webbrowser.get(using=registration)
                controller.open(url)
            return True
        except Exception as e:
            raise BrowserLaunchError(browser, url, str(e))

    def list_available_browsers(self) -> list[str]:
        """列出可用的浏览器。

        Returns:
            可用浏览器列表
        """
        return list(self._browser_map.keys())

    def is_browser_available(self, browser: str) -> bool:
        """检查浏览器是否可用。

        Args:
            browser: 浏览器名称

        Returns:
            浏览器是否可用
        """
        return browser.lower() in self._browser_map
