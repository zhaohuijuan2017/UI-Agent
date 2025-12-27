"""浏览器启动器单元测试。"""

from unittest.mock import patch

import pytest

from src.browser.browser_launcher import BrowserLauncher
from src.browser.exceptions import (
    BrowserLaunchError,
    BrowserNotFoundError,
    InvalidURLError,
)


@pytest.mark.unit
class TestBrowserLauncher:
    """浏览器启动器测试类。"""

    def test_init(self):
        """测试初始化。"""
        launcher = BrowserLauncher()
        assert launcher is not None
        assert isinstance(launcher._browser_map, dict)

    def test_validate_url_valid_https(self):
        """测试验证有效的 HTTPS URL。"""
        launcher = BrowserLauncher()
        assert launcher.validate_url("https://www.example.com") is True

    def test_validate_url_valid_http(self):
        """测试验证有效的 HTTP URL。"""
        launcher = BrowserLauncher()
        assert launcher.validate_url("http://www.example.com") is True

    def test_validate_url_with_path(self):
        """测试验证带路径的 URL。"""
        launcher = BrowserLauncher()
        assert launcher.validate_url("https://www.example.com/path/to/page") is True

    def test_validate_url_with_query(self):
        """测试验证带查询参数的 URL。"""
        launcher = BrowserLauncher()
        assert launcher.validate_url("https://www.example.com/search?q=test") is True

    def test_validate_url_with_port(self):
        """测试验证带端口号的 URL。"""
        launcher = BrowserLauncher()
        assert launcher.validate_url("http://localhost:8080") is True

    def test_validate_url_empty(self):
        """测试验证空 URL。"""
        launcher = BrowserLauncher()
        assert launcher.validate_url("") is False

    def test_validate_url_invalid_format(self):
        """测试验证无效格式的 URL。"""
        launcher = BrowserLauncher()
        assert launcher.validate_url("not-a-valid-url") is False

    def test_normalize_url_with_protocol(self):
        """测试标准化已有协议的 URL。"""
        launcher = BrowserLauncher()
        assert launcher.normalize_url("https://www.example.com") == "https://www.example.com"
        assert launcher.normalize_url("http://www.example.com") == "http://www.example.com"

    def test_normalize_url_without_protocol(self):
        """测试标准化没有协议的 URL。"""
        launcher = BrowserLauncher()
        assert launcher.normalize_url("www.example.com") == "https://www.example.com"
        assert launcher.normalize_url("example.com") == "https://example.com"

    def test_normalize_url_empty(self):
        """测试标准化空 URL。"""
        launcher = BrowserLauncher()
        with pytest.raises(InvalidURLError):
            launcher.normalize_url("")

    def test_normalize_url_invalid(self):
        """测试标准化无效 URL。"""
        launcher = BrowserLauncher()
        with pytest.raises(InvalidURLError):
            launcher.normalize_url("not a valid url!")

    def test_open_default_browser_success(self):
        """测试使用默认浏览器打开网址（成功）。"""
        launcher = BrowserLauncher()
        with patch("webbrowser.open") as mock_open:
            result = launcher.open_default_browser("https://www.example.com")
            assert result is True
            mock_open.assert_called_once_with("https://www.example.com")

    def test_open_default_browser_normalizes_url(self):
        """测试使用默认浏览器打开网址（URL 自动标准化）。"""
        launcher = BrowserLauncher()
        with patch("webbrowser.open") as mock_open:
            result = launcher.open_default_browser("www.example.com")
            assert result is True
            mock_open.assert_called_once_with("https://www.example.com")

    def test_open_default_browser_invalid_url(self):
        """测试使用默认浏览器打开网址（无效 URL）。"""
        launcher = BrowserLauncher()
        with pytest.raises(InvalidURLError):
            launcher.open_default_browser("not a valid url")

    def test_open_default_browser_failure(self):
        """测试使用默认浏览器打开网址（失败）。"""
        launcher = BrowserLauncher()
        with patch("webbrowser.open", side_effect=Exception("Browser error")):
            with pytest.raises(BrowserLaunchError):
                launcher.open_default_browser("https://www.example.com")

    def test_open_browser_with_specific_browser(self):
        """测试使用指定浏览器打开网址。"""
        launcher = BrowserLauncher()
        # 使用默认浏览器进行测试（因为特定浏览器可能未安装）
        if launcher.is_browser_available("默认"):
            with patch("webbrowser.open"):
                result = launcher.open_browser("https://www.example.com", "默认")
                assert result is True

    def test_open_browser_not_found(self):
        """测试使用不存在的浏览器打开网址。"""
        launcher = BrowserLauncher()
        # 由于浏览器不可用，应该抛出 BrowserNotFoundError
        with pytest.raises(BrowserNotFoundError):
            launcher.open_browser("https://www.example.com", "nonexistent")

    def test_list_available_browsers(self):
        """测试列出可用浏览器。"""
        launcher = BrowserLauncher()
        browsers = launcher.list_available_browsers()
        assert isinstance(browsers, list)
        # 默认浏览器应该总是可用
        assert "默认" in browsers or any(b.lower() == "默认" for b in browsers)

    def test_is_browser_available(self):
        """测试检查浏览器是否可用。"""
        launcher = BrowserLauncher()
        # 默认浏览器应该总是可用
        assert launcher.is_browser_available("默认") or launcher.is_browser_available("default")

    def test_open_browser_invalid_url(self):
        """测试打开无效 URL。"""
        launcher = BrowserLauncher()
        with pytest.raises(InvalidURLError):
            launcher.open_browser("not a url", "chrome")
