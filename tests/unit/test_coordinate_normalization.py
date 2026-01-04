"""坐标归一化还原功能的单元测试。"""

import pytest

from src.locator.visual_locator import VisualLocator


@pytest.mark.unit
class TestIsNormalizedCoordinate:
    """测试归一化坐标检测方法。"""

    def test_normalized_coordinate_true(self):
        """测试: 归一化坐标应返回True。"""
        # 归一化坐标案例: (100, 200, 300, 400) 在 (1920, 1080) 图像
        assert VisualLocator._is_normalized_coordinate((100, 200, 300, 400), (1920, 1080)) is True

    def test_pixel_coordinate_false(self):
        """测试: 像素坐标应返回False。"""
        # 像素坐标案例: (500, 600, 700, 800) 在 (800, 600) 图像
        assert VisualLocator._is_normalized_coordinate((500, 600, 700, 800), (800, 600)) is False

    def test_small_image_pixel_coordinates(self):
        """测试: 小尺寸图像的像素坐标。"""
        # 小尺寸图像 (800, 600) 与接近的坐标 (400, 300, 600, 450)
        # 应识别为像素坐标(坐标值接近图像尺寸)
        assert VisualLocator._is_normalized_coordinate((400, 300, 600, 450), (800, 600)) is False

    def test_boundary_max_value_1000(self):
        """测试: 边界情况 - 坐标值等于1000。"""
        # 坐标值等于1000 (0, 0, 1000, 1000) 在 (1920, 1080)
        assert VisualLocator._is_normalized_coordinate((0, 0, 1000, 1000), (1920, 1080)) is True

    def test_zero_coordinates(self):
        """测试: 边界情况 - 零坐标。"""
        # 零坐标 (0, 0, 0, 0) - 所有坐标≤1000
        assert VisualLocator._is_normalized_coordinate((0, 0, 0, 0), (1920, 1080)) is True

    def test_coordinate_exceeds_1000(self):
        """测试: 坐标值超过1000应返回False。"""
        # 坐标值超过1000 (100, 200, 1200, 400)
        assert VisualLocator._is_normalized_coordinate((100, 200, 1200, 400), (1920, 1080)) is False

    def test_2k_resolution_normalized(self):
        """测试: 2K分辨率下的归一化坐标。"""
        # 2K分辨率 (2560, 1440)
        assert VisualLocator._is_normalized_coordinate((500, 500, 600, 600), (2560, 1440)) is True

    def test_4k_resolution_normalized(self):
        """测试: 4K分辨率下的归一化坐标。"""
        # 4K分辨率 (3840, 2160)
        assert VisualLocator._is_normalized_coordinate((250, 250, 750, 750), (3840, 2160)) is True


@pytest.mark.unit
class TestDenormalizeBbox:
    """测试坐标转换方法。"""

    def test_full_hd_conversion(self):
        """测试: Full HD (1920×1080) 转换。"""
        # (500, 500, 600, 600) 应转换为 (960, 540, 1152, 648)
        result = VisualLocator._denormalize_bbox((500, 500, 600, 600), (1920, 1080))
        assert result == (960, 540, 1152, 648)

    def test_2k_conversion(self):
        """测试: 2K (2560×1440) 转换。"""
        # (0, 0, 500, 1000) 应转换为 (0, 0, 1280, 1440)
        result = VisualLocator._denormalize_bbox((0, 0, 500, 1000), (2560, 1440))
        assert result == (0, 0, 1280, 1440)

    def test_4k_conversion(self):
        """测试: 4K (3840×2160) 转换。"""
        # (250, 250, 750, 750) 应转换为 (960, 540, 2880, 1620)
        result = VisualLocator._denormalize_bbox((250, 250, 750, 750), (3840, 2160))
        assert result == (960, 540, 2880, 1620)

    def test_hd_conversion(self):
        """测试: HD (1280×720) 转换。"""
        # (500, 250, 1000, 750) 应转换为 (640, 180, 1280, 540)
        result = VisualLocator._denormalize_bbox((500, 250, 1000, 750), (1280, 720))
        assert result == (640, 180, 1280, 540)

    def test_boundary_right_edge(self):
        """测试: 边界情况 - 超出右边界。"""
        # (900, 500, 1050, 600) 在 (1920, 1080)
        # x2应被裁剪为1920
        result = VisualLocator._denormalize_bbox((900, 500, 1050, 600), (1920, 1080))
        assert result == (1728, 540, 1920, 648)

    def test_boundary_left_edge(self):
        """测试: 边界情况 - 超出左边界(负坐标)。"""
        # (-50, 100, 200, 300) 在 (1920, 1080)
        # x1应被裁剪为0
        result = VisualLocator._denormalize_bbox((-50, 100, 200, 300), (1920, 1080))
        assert result[0] == 0  # x1
        assert result[2] == 384  # x2

    def test_boundary_bottom_edge(self):
        """测试: 边界情况 - 超出下边界。"""
        # (100, 900, 200, 1050) 在 (1920, 1080)
        # y2应被裁剪为1080
        result = VisualLocator._denormalize_bbox((100, 900, 200, 1050), (1920, 1080))
        assert result == (192, 972, 384, 1080)

    def test_zero_width_bbox(self):
        """测试: 边界情况 - 零宽度bbox。"""
        # (500, 500, 500, 600) - 宽度为0
        result = VisualLocator._denormalize_bbox((500, 500, 500, 600), (1920, 1080))
        # x2应至少为x1+1
        assert result[2] == result[0] + 1

    def test_zero_height_bbox(self):
        """测试: 边界情况 - 零高度bbox。"""
        # (500, 500, 600, 500) - 高度为0
        result = VisualLocator._denormalize_bbox((500, 500, 600, 500), (1920, 1080))
        # y2应至少为y1+1
        assert result[3] == result[1] + 1

    def test_floating_point_precision(self):
        """测试: 浮点数精度。"""
        # (333, 333, 666, 666) 在 (1920, 1080)
        result = VisualLocator._denormalize_bbox((333, 333, 666, 666), (1920, 1080))
        # 验证计算精度
        expected = (639, 359, 1278, 719)
        assert result == expected

    def test_full_image_bbox(self):
        """测试: 整个图像的bbox。"""
        # (0, 0, 1000, 1000) 应转换为完整图像尺寸
        result = VisualLocator._denormalize_bbox((0, 0, 1000, 1000), (1920, 1080))
        assert result == (0, 0, 1920, 1080)

    def test_small_bbox_precision(self):
        """测试: 小尺寸bbox的精度。"""
        # (10, 10, 20, 30) 在 (1920, 1080)
        result = VisualLocator._denormalize_bbox((10, 10, 20, 30), (1920, 1080))
        # 验证转换后的bbox仍然合理
        assert result[2] > result[0]  # x2 > x1
        assert result[3] > result[1]  # y2 > y1
        assert result[0] >= 0 and result[1] >= 0  # 非负
        assert result[2] <= 1920 and result[3] <= 1080  # 在边界内
