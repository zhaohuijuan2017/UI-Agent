"""屏幕捕获模块。"""

import time
from pathlib import Path
from typing import Optional

import mss
import mss.tools
from PIL import Image

from src.config.schema import SystemConfig


class ScreenshotCapture:
    """屏幕截图捕获器。"""

    def __init__(self, config: SystemConfig) -> None:
        """初始化截图捕获器。

        Args:
            config: 系统配置
        """
        self.config = config
        self.screenshot_dir = Path(config.screenshot_dir)
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)

        self._screenshot_history: list[Path] = []
        self._max_history = 10

        # mss 实例
        self._monitor = mss.mss()

    def capture_fullscreen(self) -> Image.Image:
        """捕获全屏截图。

        Returns:
            截图图像对象
        """
        monitor = self._monitor.monitors[0]  # 主显示器
        screenshot = self._monitor.grab(monitor)

        # 转换为 PIL Image
        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return img

    def capture_region(self, x: int, y: int, width: int, height: int) -> Image.Image:
        """捕获指定区域的截图。

        Args:
            x: 起始 X 坐标
            y: 起始 Y 坐标
            width: 宽度
            height: 高度

        Returns:
            截图图像对象
        """
        monitor = {"top": y, "left": x, "width": width, "height": height}
        screenshot = self._monitor.grab(monitor)

        img = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return img

    def capture_window_by_title(self, title: str) -> Optional[Image.Image]:
        """根据窗口标题捕获窗口截图。

        注意：这是简化实现，实际可能需要使用 pygetwindow 或其他库

        Args:
            title: 窗口标题（部分匹配）

        Returns:
            截图图像对象，如果未找到窗口则返回 None
        """
        try:
            import pygetwindow as gw

            windows = gw.getWindowsWithTitle(title)
            if not windows:
                return None

            window = windows[0]
            if window.isMinimized:
                return None

            # 获取窗口位置和大小
            x, y = window.left, window.top
            width, height = window.width, window.height

            return self.capture_region(int(x), int(y), int(width), int(height))
        except ImportError:
            # 如果没有安装 pygetwindow，回退到全屏
            return self.capture_fullscreen()
        except Exception:
            return None

    def save_screenshot(
        self,
        img: Image.Image,
        filename: str | None = None,
        add_to_history: bool = True,
    ) -> Path:
        """保存截图到文件。

        Args:
            img: 图像对象
            filename: 文件名，如果不指定则自动生成
            add_to_history: 是否添加到历史记录

        Returns:
            保存的文件路径
        """
        if filename is None:
            timestamp = int(time.time() * 1000)
            filename = f"screenshot_{timestamp}.png"

        filepath = self.screenshot_dir / filename
        img.save(filepath)

        if add_to_history:
            self._add_to_history(filepath)

        return filepath

    def _add_to_history(self, filepath: Path) -> None:
        """添加截图到历史记录。

        Args:
            filepath: 截图文件路径
        """
        self._screenshot_history.append(filepath)

        # 限制历史记录大小
        while len(self._screenshot_history) > self._max_history:
            old = self._screenshot_history.pop(0)
            # 可选：删除旧文件
            # old.unlink(missing_ok=True)

    def get_history(self) -> list[Path]:
        """获取截图历史记录。

        Returns:
            历史截图路径列表
        """
        return self._screenshot_history.copy()

    def clear_history(self) -> None:
        """清空截图历史记录。"""
        self._screenshot_history.clear()

    def capture_and_save(
        self,
        filename: str | None = None,
        region: tuple[int, int, int, int] | None = None,
    ) -> Path:
        """捕获并保存截图。

        Args:
            filename: 文件名
            region: 区域 (x, y, width, height)

        Returns:
            保存的文件路径
        """
        if region:
            img = self.capture_region(*region)
        else:
            img = self.capture_fullscreen()

        return self.save_screenshot(img, filename)
