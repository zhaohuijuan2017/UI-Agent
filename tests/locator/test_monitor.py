"""多屏显示器支持测试。"""

import pytest
from PIL import Image

from src.locator.screenshot import ScreenshotCapture
from src.locator.visual_locator import VisualLocator
from src.config.schema import SystemConfig


@pytest.mark.unit
class TestMonitorSupport:
    """多屏显示器支持测试类。"""

    @pytest.fixture
    def capture(self, temp_config_dir):
        """创建捕获器实例。"""
        config = SystemConfig(screenshot_dir=str(temp_config_dir))
        return ScreenshotCapture(config)

    def test_get_monitors(self, capture):
        """测试获取所有显示器信息。"""
        monitors = capture.get_monitors()

        # 应该至少有一个显示器（虚拟屏幕）
        assert len(monitors) >= 1

        # 第一个显示器应该是虚拟屏幕（所有显示器合并）
        assert "top" in monitors[0]
        assert "left" in monitors[0]
        assert "width" in monitors[0]
        assert "height" in monitors[0]

        # 打印显示器信息用于调试
        print(f"\n检测到 {len(monitors)} 个显示器:")
        for i, m in enumerate(monitors):
            print(f"  显示器 {i}: top={m['top']}, left={m['left']}, "
                  f"width={m['width']}, height={m['height']}")

    def test_capture_fullscreen_default(self, capture):
        """测试默认捕获全屏（虚拟屏幕）。"""
        screenshot = capture.capture_fullscreen()
        assert screenshot is not None
        assert screenshot.size[0] > 0
        assert screenshot.size[1] > 0
        print(f"\n虚拟屏幕尺寸: {screenshot.size}")

    def test_capture_specific_monitor(self, capture):
        """测试捕获指定显示器截图。"""
        monitors = capture.get_monitors()

        # 测试捕获虚拟屏幕（monitor_index=0）
        screenshot_0 = capture.capture_fullscreen(monitor_index=0)
        assert screenshot_0 is not None
        assert screenshot_0.size[0] > 0
        assert screenshot_0.size[1] > 0
        print(f"\n显示器 0 (虚拟屏幕) 尺寸: {screenshot_0.size}")

        # 如果有多个显示器，测试第一个物理显示器
        if len(monitors) > 1:
            screenshot_1 = capture.capture_fullscreen(monitor_index=1)
            assert screenshot_1 is not None
            assert screenshot_1.size[0] > 0
            assert screenshot_1.size[1] > 0
            print(f"显示器 1 (第一个物理显示器) 尺寸: {screenshot_1.size}")

            # 虚拟屏幕应该比单个物理显示器大（或相等）
            virtual_area = screenshot_0.size[0] * screenshot_0.size[1]
            physical_area = screenshot_1.size[0] * screenshot_1.size[1]
            assert virtual_area >= physical_area

    def test_capture_monitor_method(self, capture):
        """测试 capture_monitor 便捷方法。"""
        monitors = capture.get_monitors()

        # 如果有多个显示器，测试 capture_monitor 方法
        if len(monitors) > 1:
            # capture_monitor(1) 应该等同于 capture_fullscreen(monitor_index=1)
            screenshot = capture.capture_monitor(1)
            assert screenshot is not None
            assert screenshot.size[0] > 0
            assert screenshot.size[1] > 0
            print(f"\ncapture_monitor(1) 尺寸: {screenshot.size}")

    def test_capture_monitor_out_of_range(self, capture):
        """测试捕获超出范围的显示器。"""
        monitors = capture.get_monitors()

        # 尝试捕获不存在的显示器
        with pytest.raises(ValueError, match="显示器索引.*超出范围"):
            capture.capture_fullscreen(monitor_index=999)

        with pytest.raises(ValueError, match="显示器索引.*超出范围"):
            capture.capture_fullscreen(monitor_index=-1)

    def test_visual_locator_default_monitor(self, capture):
        """测试 VisualLocator 默认显示器设置。"""
        # 创建定位器，不指定 monitor_index（默认 0）
        locator = VisualLocator(
            api_key="test_key",
            screenshot_capture=capture,
            vision_enabled=False,  # 禁用视觉识别以避免 API 调用
        )

        # 默认应该使用显示器 0
        assert locator.get_monitor_index() == 0

    def test_visual_locator_set_monitor(self, capture):
        """测试 VisualLocator 设置显示器。"""
        locator = VisualLocator(
            api_key="test_key",
            screenshot_capture=capture,
            monitor_index=2,
            vision_enabled=False,
        )

        # 应该使用显示器 2
        assert locator.get_monitor_index() == 2

        # 动态更改显示器
        locator.set_monitor_index(1)
        assert locator.get_monitor_index() == 1

    def test_visual_locator_capture_with_monitor(self, capture):
        """测试 VisualLocator 使用指定显示器截图。"""
        monitors = capture.get_monitors()

        locator = VisualLocator(
            api_key="test_key",
            screenshot_capture=capture,
            monitor_index=0,
            vision_enabled=False,
        )

        # 使用默认显示器定位（这里不真正调用 API，只测试截图）
        # 由于禁用了视觉识别且没有 target_filter，会返回空列表
        # 但我们可以测试内部的截图捕获是否正常工作
        if len(monitors) > 0:
            screenshot = capture.capture_fullscreen(monitor_index=0)
            assert screenshot is not None

        if len(monitors) > 1:
            # 测试使用不同显示器
            screenshot = capture.capture_fullscreen(monitor_index=1)
            assert screenshot is not None
            print(f"\n使用显示器 1 截图尺寸: {screenshot.size}")

    def test_monitor_info_completeness(self, capture):
        """测试显示器信息的完整性。"""
        monitors = capture.get_monitors()

        for i, monitor in enumerate(monitors):
            # 每个显示器必须包含这些字段
            required_fields = ["top", "left", "width", "height"]
            for field in required_fields:
                assert field in monitor, f"显示器 {i} 缺少字段: {field}"
                assert isinstance(monitor[field], int), f"显示器 {i} 的 {field} 应该是整数"
                assert monitor[field] >= 0, f"显示器 {i} 的 {field} 应该 >= 0"

            # 宽度和高度必须大于 0
            assert monitor["width"] > 0, f"显示器 {i} 的宽度必须 > 0"
            assert monitor["height"] > 0, f"显示器 {i} 的高度必须 > 0"

    def test_save_screenshot_from_different_monitors(self, capture, temp_config_dir):
        """测试保存不同显示器的截图。"""
        monitors = capture.get_monitors()

        saved_files = []

        # 保存虚拟屏幕截图
        screenshot_0 = capture.capture_fullscreen(monitor_index=0)
        filepath_0 = capture.save_screenshot(screenshot_0, "monitor_0.png")
        saved_files.append(filepath_0)
        assert filepath_0.exists()

        # 如果有多个显示器，保存第一个物理显示器截图
        if len(monitors) > 1:
            screenshot_1 = capture.capture_fullscreen(monitor_index=1)
            filepath_1 = capture.save_screenshot(screenshot_1, "monitor_1.png")
            saved_files.append(filepath_1)
            assert filepath_1.exists()

        print(f"\n已保存 {len(saved_files)} 个显示器截图到 {temp_config_dir}")
