"""视觉定位坐标归一化还原的集成测试。"""

import json
from unittest.mock import Mock, patch

import pytest
from PIL import Image

from src.locator.visual_locator import VisualLocator
from src.models.element import UIElement


class TestVisualLocatorNormalizationIntegration:
    """测试VisualLocator的坐标归一化还原集成。"""

    @pytest.fixture
    def mock_screenshot(self):
        """创建模拟截图。"""
        # 创建1920x1080的测试图像
        return Image.new("RGB", (1920, 1080), color="white")

    @pytest.fixture
    def locator(self):
        """创建VisualLocator实例。"""
        with patch("src.locator.visual_locator.ZhipuAI"):
            locator = VisualLocator(
                api_key="test_key",
                model="glm-4v-flash",
                vision_enabled=True,
            )
            return locator

    def test_normalized_coordinates_conversion(self, locator, mock_screenshot):
        """测试: 归一化坐标能正确转换。"""
        # 模拟LLM返回归一化坐标
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            [
                {
                    "element_type": "button",
                    "description": "测试按钮",
                    "bbox": [500, 500, 600, 600],  # 归一化坐标
                    "confidence": 0.9,
                }
            ]
        )

        with patch.object(locator.client.chat.completions, "create", return_value=mock_response):
            elements = locator.locate("查找按钮", screenshot=mock_screenshot)

        # 验证转换后的坐标
        assert len(elements) == 1
        # (500, 500, 600, 600) 在 1920x1080 应转换为 (960, 540, 1152, 648)
        assert elements[0].bbox == (960, 540, 1152, 648)
        assert elements[0].element_type == "button"
        assert elements[0].confidence == 0.9

    def test_pixel_coordinates_no_conversion(self, locator, mock_screenshot):
        """测试: 像素坐标不进行转换。"""
        # 创建小尺寸图像(800x600)
        small_screenshot = Image.new("RGB", (800, 600), color="white")

        # 模拟LLM返回像素坐标(坐标值接近图像尺寸)
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            [
                {
                    "element_type": "button",
                    "description": "测试按钮",
                    "bbox": [400, 300, 500, 400],  # 像素坐标
                    "confidence": 0.9,
                }
            ]
        )

        with patch.object(locator.client.chat.completions, "create", return_value=mock_response):
            elements = locator.locate("查找按钮", screenshot=small_screenshot)

        # 验证坐标未转换
        assert len(elements) == 1
        assert elements[0].bbox == (400, 300, 500, 400)

    def test_multiple_elements_conversion(self, locator, mock_screenshot):
        """测试: 多个元素的坐标转换。"""
        # 模拟LLM返回多个元素
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            [
                {
                    "element_type": "button",
                    "description": "按钮1",
                    "bbox": [100, 100, 200, 200],  # 归一化坐标
                    "confidence": 0.9,
                },
                {
                    "element_type": "button",
                    "description": "按钮2",
                    "bbox": [300, 300, 400, 400],  # 归一化坐标
                    "confidence": 0.85,
                },
                {
                    "element_type": "text",
                    "description": "文本",
                    "bbox": [500, 500, 700, 600],  # 归一化坐标
                    "confidence": 0.95,
                },
            ]
        )

        with patch.object(locator.client.chat.completions, "create", return_value=mock_response):
            elements = locator.locate("查找所有元素", screenshot=mock_screenshot)

        # 验证所有元素都正确转换
        assert len(elements) == 3
        # 第一个元素: (100, 100, 200, 200) -> (192, 108, 384, 216)
        assert elements[0].bbox == (192, 108, 384, 216)
        # 第二个元素: (300, 300, 400, 400) -> (576, 324, 768, 432)
        assert elements[1].bbox == (576, 324, 768, 432)
        # 第三个元素: (500, 500, 700, 600) -> (960, 540, 1344, 648)
        assert elements[2].bbox == (960, 540, 1344, 648)

    def test_different_resolutions(self, locator):
        """测试: 不同分辨率截图的坐标转换。"""
        test_cases = [
            # (分辨率, 输入坐标, 期望像素坐标)
            # Full HD: 归一化坐标转换
            ((1920, 1080), (500, 500, 600, 600), (960, 540, 1152, 648)),
            # 2K: 归一化坐标转换
            ((2560, 1440), (500, 500, 600, 600), (1280, 720, 1536, 864)),
            # 4K: 归一化坐标转换
            ((3840, 2160), (250, 250, 750, 750), (960, 540, 2880, 1620)),
            # 1280x720: (500, 250, 1000, 750) 是归一化坐标(最大值=1000)
            # 转换: x1=(500/1000)*1280=640, y1=(250/1000)*720=180, x2=(1000/1000)*1280=1280, y2=(750/1000)*720=540
            ((1280, 720), (500, 250, 1000, 750), (640, 180, 1280, 540)),
        ]

        for resolution, input_bbox, expected_bbox in test_cases:
            screenshot = Image.new("RGB", resolution, color="white")

            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps(
                [
                    {
                        "element_type": "button",
                        "description": "测试按钮",
                        "bbox": list(input_bbox),
                        "confidence": 0.9,
                    }
                ]
            )

            with patch.object(locator.client.chat.completions, "create", return_value=mock_response):
                elements = locator.locate("查找按钮", screenshot=screenshot)

            assert len(elements) == 1
            assert elements[0].bbox == expected_bbox, f"分辨率 {resolution} 转换失败"

    def test_bbox_within_image_bounds(self, locator, mock_screenshot):
        """测试: 转换后的bbox在图像范围内。"""
        width, height = mock_screenshot.size

        # 模拟边界坐标 (0, 0, 1000, 1000)
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            [
                {
                    "element_type": "button",
                    "description": "全屏按钮",
                    "bbox": [0, 0, 1000, 1000],
                    "confidence": 0.9,
                }
            ]
        )

        with patch.object(locator.client.chat.completions, "create", return_value=mock_response):
            elements = locator.locate("查找按钮", screenshot=mock_screenshot)

        assert len(elements) == 1
        bbox = elements[0].bbox

        # 验证bbox在图像范围内
        assert 0 <= bbox[0] < bbox[2] <= width  # x1 < x2 <= width
        assert 0 <= bbox[1] < bbox[3] <= height  # y1 < y2 <= height
        # 验证完整覆盖
        assert bbox == (0, 0, width, height)

    def test_center_point_calculation(self, locator, mock_screenshot):
        """测试: 转换后的bbox中心点计算正确。"""
        # 归一化坐标 (400, 400, 600, 600)
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            [
                {
                    "element_type": "button",
                    "description": "中心按钮",
                    "bbox": [400, 400, 600, 600],
                    "confidence": 0.9,
                }
            ]
        )

        with patch.object(locator.client.chat.completions, "create", return_value=mock_response):
            elements = locator.locate("查找按钮", screenshot=mock_screenshot)

        assert len(elements) == 1
        element = elements[0]

        # (400, 400, 600, 600) 在 1920x1080 应转换为 (768, 432, 1152, 648)
        assert element.bbox == (768, 432, 1152, 648)

        # 验证中心点
        center = element.center
        expected_center = ((768 + 1152) // 2, (432 + 648) // 2)
        assert center == expected_center
        assert center == (960, 540)  # 图像中心

    def test_element_preservation(self, locator, mock_screenshot):
        """测试: 坐标转换不影响其他元素属性。"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            [
                {
                    "element_type": "button",
                    "description": "测试按钮",
                    "bbox": [500, 500, 600, 600],
                    "confidence": 0.95,
                }
            ]
        )

        with patch.object(locator.client.chat.completions, "create", return_value=mock_response):
            elements = locator.locate("查找按钮", screenshot=mock_screenshot)

        assert len(elements) == 1
        element = elements[0]

        # 验证其他属性保持不变
        assert element.element_type == "button"
        assert element.description == "测试按钮"
        assert element.confidence == 0.95
        assert element.metadata is None

        # 验证只有bbox被转换
        assert element.bbox == (960, 540, 1152, 648)
