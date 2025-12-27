"""浏览器自动化控制器单元测试（基于 OCR）。"""

from unittest.mock import MagicMock, patch

import pytest

from src.browser.automation import BrowserAutomation
from src.browser.exceptions import (
    ElementNotFoundError,
    OperationTimeoutError,
)
from src.models.element import UIElement


@pytest.mark.unit
class TestBrowserAutomation:
    """浏览器自动化控制器测试类。"""

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    def test_init_default(self, mock_screenshot, mock_locator):
        """测试默认初始化。"""
        automation = BrowserAutomation()
        assert automation is not None
        assert automation.api_key is None
        assert automation.model == "glm-4-flash"
        assert automation.screenshot is not None
        assert automation.locator is not None

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    def test_init_with_api_key(self, mock_screenshot, mock_locator):
        """测试使用 API Key 初始化。"""
        automation = BrowserAutomation(api_key="test-key", model="glm-4v")
        assert automation.api_key == "test-key"
        assert automation.model == "glm-4v"

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    @patch("src.browser.automation.pyautogui.click")
    def test_click_success(self, mock_click, mock_screenshot, mock_locator):
        """测试点击元素（成功）。"""
        automation = BrowserAutomation()

        # Mock locator
        mock_element = UIElement(
            element_type="button",
            description="Submit",
            bbox=(100, 200, 150, 220),  # x1, y1, x2, y2
            confidence=0.9,
        )

        with patch.object(
            automation.locator, "locate", return_value=[mock_element]
        ):
            automation.click("Submit")

            mock_click.assert_called_once_with(125, 210)  # Center point

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    def test_click_element_not_found(self, mock_screenshot, mock_locator):
        """测试点击元素（未找到）。"""
        automation = BrowserAutomation()

        with patch.object(automation.locator, "locate", return_value=[]):
            with pytest.raises(ElementNotFoundError) as exc_info:
                automation.click("NonExistent")

            assert "NonExistent" in str(exc_info.value)

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    @patch("src.browser.automation.pyautogui.scroll")
    def test_scroll_down(self, mock_scroll, mock_screenshot, mock_locator):
        """测试向下滚动。"""
        automation = BrowserAutomation()

        automation.scroll(direction="down", distance=3)

        assert mock_scroll.call_count == 3
        for call in mock_scroll.call_args_list:
            args, kwargs = call
            assert args[0] == -300  # Negative for down

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    @patch("src.browser.automation.pyautogui.scroll")
    def test_scroll_up(self, mock_scroll, mock_screenshot, mock_locator):
        """测试向上滚动。"""
        automation = BrowserAutomation()

        automation.scroll(direction="up", distance=2)

        assert mock_scroll.call_count == 2
        for call in mock_scroll.call_args_list:
            args, kwargs = call
            assert args[0] == 300  # Positive for up

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    @patch("src.browser.automation.pyautogui.hscroll")
    def test_scroll_left(self, mock_hscroll, mock_screenshot, mock_locator):
        """测试向左滚动。"""
        automation = BrowserAutomation()

        automation.scroll(direction="left", distance=2)

        assert mock_hscroll.call_count == 2
        for call in mock_hscroll.call_args_list:
            args, kwargs = call
            assert args[0] == 300  # Positive for left

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    @patch("src.browser.automation.pyautogui.hscroll")
    def test_scroll_right(self, mock_hscroll, mock_screenshot, mock_locator):
        """测试向右滚动。"""
        automation = BrowserAutomation()

        automation.scroll(direction="right", distance=1)

        mock_hscroll.assert_called_once_with(-300)  # Negative for right

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    def test_scroll_invalid_direction(self, mock_screenshot, mock_locator):
        """测试无效的滚动方向。"""
        automation = BrowserAutomation()

        with pytest.raises(ValueError) as exc_info:
            automation.scroll(direction="invalid")

        assert "invalid" in str(exc_info.value)

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    @patch("src.browser.automation.pyautogui.click")
    @patch("src.browser.automation.pyautogui.typewrite")
    def test_type_text(self, mock_typewrite, mock_click, mock_screenshot, mock_locator):
        """测试输入文本。"""
        automation = BrowserAutomation()

        # Mock locator
        mock_element = UIElement(
            element_type="input",
            description="Search",
            bbox=(100, 200, 200, 230),  # x1, y1, x2, y2
            confidence=0.9,
        )

        with patch.object(
            automation.locator, "locate", return_value=[mock_element]
        ):
            automation.type_text("Search", "test query")

            mock_click.assert_called_once()
            mock_typewrite.assert_called_once_with("test query")

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    @patch("src.browser.automation.pyautogui.click")
    @patch("src.browser.automation.pyautogui.hotkey")
    @patch("src.browser.automation.pyautogui.press")
    @patch("src.browser.automation.pyautogui.typewrite")
    def test_type_text_with_clear(
        self, mock_typewrite, mock_press, mock_hotkey, mock_click, mock_screenshot, mock_locator
    ):
        """测试输入文本（先清空）。"""
        automation = BrowserAutomation()

        # Mock locator
        mock_element = UIElement(
            element_type="input",
            description="Search",
            bbox=(100, 200, 200, 230),  # x1, y1, x2, y2
            confidence=0.9,
        )

        with patch.object(
            automation.locator, "locate", return_value=[mock_element]
        ):
            automation.type_text("Search", "new text", clear=True)

            mock_click.assert_called_once()
            mock_hotkey.assert_called_once_with("ctrl", "a")
            mock_press.assert_called_once_with("backspace")
            mock_typewrite.assert_called_once_with("new text")

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    def test_type_text_element_not_found(self, mock_screenshot, mock_locator):
        """测试输入文本（输入框未找到）。"""
        automation = BrowserAutomation()

        with patch.object(automation.locator, "locate", return_value=[]):
            with pytest.raises(ElementNotFoundError):
                automation.type_text("NonExistent", "text")

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    @patch("src.browser.automation.pyautogui.press")
    def test_press_key(self, mock_press, mock_screenshot, mock_locator):
        """测试按键操作。"""
        automation = BrowserAutomation()

        automation.press_key("Enter")

        mock_press.assert_called_once_with("Enter")

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    def test_wait_for_element_success(self, mock_screenshot, mock_locator):
        """测试等待元素（成功）。"""
        automation = BrowserAutomation()

        # Mock locator - first call returns empty, second returns element
        mock_element = UIElement(
            element_type="text",
            description="Loading",
            bbox=(100, 200, 150, 220),  # x1, y1, x2, y2
            confidence=0.9,
        )

        with patch.object(
            automation.locator, "locate", side_effect=[[], [mock_element]]
        ):
            # Should return without error when element is found
            automation.wait_for_element("Loading", timeout=1000)

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    def test_wait_for_element_timeout(self, mock_screenshot, mock_locator):
        """测试等待元素（超时）。"""
        automation = BrowserAutomation()

        with patch.object(automation.locator, "locate", return_value=[]):
            with pytest.raises(OperationTimeoutError) as exc_info:
                automation.wait_for_element("Loading", timeout=100)

            assert "wait_for_element" in str(exc_info.value)

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    def test_is_element_visible_true(self, mock_screenshot, mock_locator):
        """测试检查元素可见性（可见）。"""
        automation = BrowserAutomation()

        mock_element = UIElement(
            element_type="button",
            description="Button",
            bbox=(100, 200, 150, 220),  # x1, y1, x2, y2
            confidence=0.9,
        )

        with patch.object(
            automation.locator, "locate", return_value=[mock_element]
        ):
            result = automation.is_element_visible("Button")
            assert result is True

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    def test_is_element_visible_false(self, mock_screenshot, mock_locator):
        """测试检查元素可见性（不可见）。"""
        automation = BrowserAutomation()

        with patch.object(automation.locator, "locate", return_value=[]):
            result = automation.is_element_visible("Button")
            assert result is False

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    def test_is_element_enabled(self, mock_screenshot, mock_locator):
        """测试检查元素是否启用。"""
        automation = BrowserAutomation()

        mock_element = UIElement(
            element_type="button",
            description="Button",
            bbox=(100, 200, 150, 220),  # x1, y1, x2, y2
            confidence=0.9,
        )

        with patch.object(
            automation.locator, "locate", return_value=[mock_element]
        ):
            result = automation.is_element_enabled("Button")
            assert result is True

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    def test_get_element_text(self, mock_screenshot, mock_locator):
        """测试获取元素文本。"""
        automation = BrowserAutomation()

        text = automation.get_element_text("Button")
        # Simplified implementation returns the description
        assert text == "Button"

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    def test_get_element_attribute(self, mock_screenshot, mock_locator):
        """测试获取元素属性。"""
        automation = BrowserAutomation()

        attr = automation.get_element_attribute("Button", "href")
        # Simplified implementation returns empty string
        assert attr == ""

    @patch("src.browser.automation.VisualLocator")
    @patch("src.browser.automation.ScreenshotCapture")
    def test_close(self, mock_screenshot, mock_locator):
        """测试关闭浏览器自动化。"""
        automation = BrowserAutomation()

        # Should not raise any error
        automation.close()
