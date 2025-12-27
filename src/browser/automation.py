"""浏览器自动化控制器模块（基于 OCR + OpenCV）。"""

import logging
import time
from pathlib import Path
from typing import Any

import pyautogui

from src.browser.exceptions import (
    ElementNotFoundError,
    OperationTimeoutError,
    ElementNotInteractableError,
)
from src.config.schema import SystemConfig
from src.locator.screenshot import ScreenshotCapture
from src.locator.visual_locator import VisualLocator

logger = logging.getLogger(__name__)


class BrowserAutomation:
    """浏览器自动化控制器（基于视觉定位）。"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "glm-4-flash",
        config: SystemConfig | None = None,
    ) -> None:
        """初始化浏览器自动化控制器。

        Args:
            api_key: 智谱 AI API Key
            model: 使用的模型名称
            config: 系统配置（可选）
        """
        self.api_key = api_key
        self.model = model

        # 如果没有提供配置，创建一个最小配置
        if config is None:
            config = SystemConfig(
                screenshot_dir="screenshots/",
                log_file="logs/ide_controller.log",
                log_level="INFO",
            )

        # 初始化截图和定位器
        self.screenshot = ScreenshotCapture(config)
        self.locator = VisualLocator(
            api_key=api_key,
            model=model,
            screenshot_capture=self.screenshot,
            vision_enabled=True,  # 启用视觉识别
        )

        # 设置坐标偏移（如果有需要）
        self.locator.set_coordinate_offset([0, 0])

    def click(self, text: str, timeout: int = 5000) -> None:
        """点击包含指定文本的页面元素。

        Args:
            text: 元素文本内容
            timeout: 超时时间（毫秒）

        Raises:
            ElementNotFoundError: 元素未找到
        """
        logger.info(f"查找元素: {text}")

        # 捕获屏幕截图
        screenshot = self.screenshot.capture_fullscreen()

        # 使用视觉定位器查找元素
        elements = self.locator.locate(
            f"在截图中找到包含文本 '{text}' 的元素",
            screenshot,
            target_filter=text,
        )

        if not elements:
            raise ElementNotFoundError(text, timeout)

        # 获取第一个元素的中心坐标
        element = elements[0]
        x, y = element.center

        logger.info(f"点击元素: {text} at ({x}, {y})")
        pyautogui.click(x, y)
        time.sleep(0.2)  # 等待点击生效

    def scroll(self, direction: str = "down", distance: int | None = None) -> None:
        """滚动页面。

        Args:
            direction: 滚动方向（up、down、left、right）
            distance: 滚动距离（点击次数），默认为 3 次
        """
        if distance is None:
            distance = 3  # 默认滚动 3 次

        logger.info(f"滚动页面: direction={direction}, distance={distance}")

        match direction:
            case "down":
                for _ in range(distance):
                    pyautogui.scroll(-300)  # 向下滚动
                    time.sleep(0.1)
            case "up":
                for _ in range(distance):
                    pyautogui.scroll(300)  # 向上滚动
                    time.sleep(0.1)
            case "left":
                for _ in range(distance):
                    pyautogui.hscroll(300)  # 向左滚动
                    time.sleep(0.1)
            case "right":
                for _ in range(distance):
                    pyautogui.hscroll(-300)  # 向右滚动
                    time.sleep(0.1)
            case _:
                raise ValueError(f"不支持的滚动方向: {direction}")

    def type_text(self, text: str, input_text: str, clear: bool = False) -> None:
        """在输入框中输入文本。

        Args:
            text: 输入框的描述文本（用于定位）
            input_text: 要输入的文本
            clear: 是否先清空输入框

        Raises:
            ElementNotFoundError: 输入框未找到
        """
        logger.info(f"查找输入框: {text}")

        # 捕获屏幕截图
        screenshot = self.screenshot.capture_fullscreen()

        # 使用视觉定位器查找输入框
        elements = self.locator.locate(
            f"在截图中找到输入框（包含文本 '{text}' 或描述为 '{text}'）",
            screenshot,
            target_filter=text,
        )

        if not elements:
            raise ElementNotFoundError(text, 5000)

        # 获取第一个元素的中心坐标
        element = elements[0]
        x, y = element.center

        logger.info(f"点击输入框: {text} at ({x}, {y})")
        pyautogui.click(x, y)
        time.sleep(0.2)

        # 如果需要清空
        if clear:
            logger.info("清空输入框")
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.press('backspace')
            time.sleep(0.1)

        logger.info(f"输入文本: {input_text}")
        pyautogui.typewrite(input_text)
        time.sleep(0.2)

    def press_key(self, key: str) -> None:
        """模拟按键操作。

        Args:
            key: 按键名称（如 Enter、Tab、Escape 等）
        """
        logger.info(f"按下按键: {key}")
        pyautogui.press(key)
        time.sleep(0.2)

    def wait_for_element(self, text: str, timeout: int = 5000) -> None:
        """等待元素出现。

        Args:
            text: 元素文本
            timeout: 超时时间（毫秒）

        Raises:
            OperationTimeoutError: 等待超时
        """
        logger.info(f"等待元素出现: {text}")

        start_time = time.time()
        timeout_sec = timeout / 1000

        while time.time() - start_time < timeout_sec:
            screenshot = self.screenshot.capture_fullscreen()
            elements = self.locator.locate(
                f"在截图中找到包含文本 '{text}' 的元素",
                screenshot,
                target_filter=text,
            )

            if elements:
                logger.info(f"元素已出现: {text}")
                return

            time.sleep(0.5)  # 每 0.5 秒检查一次

        raise OperationTimeoutError(f"wait_for_element({text})", timeout)

    def is_element_visible(self, text: str) -> bool:
        """检查元素是否可见。

        Args:
            text: 元素文本

        Returns:
            元素是否可见
        """
        try:
            screenshot = self.screenshot.capture_fullscreen()
            elements = self.locator.locate(
                f"在截图中找到包含文本 '{text}' 的元素",
                screenshot,
                target_filter=text,
            )
            return len(elements) > 0
        except Exception:
            return False

    def is_element_enabled(self, text: str) -> bool:
        """检查元素是否启用（通过颜色判断）。

        Args:
            text: 元素文本

        Returns:
            元素是否启用（简化实现，假设可见就是启用）
        """
        return self.is_element_visible(text)

    def get_element_text(self, text: str) -> str:
        """获取元素文本内容。

        Args:
            text: 元素描述

        Returns:
            元素文本内容（简化实现，直接返回描述）
        """
        # 简化实现：直接返回文本描述
        # 实际应用中可以使用 OCR 获取元素周围的实际文本
        return text

    def get_element_attribute(self, text: str, attribute: str) -> str:
        """获取元素属性值。

        Args:
            text: 元素描述
            attribute: 属性名称

        Returns:
            属性值（简化实现）
        """
        # 简化实现：基于视觉定位无法直接获取 DOM 属性
        # 返回空字符串
        return ""

    def close(self) -> None:
        """关闭浏览器自动化（无需操作）。"""
        logger.info("浏览器自动化会话结束")
