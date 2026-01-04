"""坐标归一化还原的性能基准测试。"""

import timeit

import pytest

from src.locator.visual_locator import VisualLocator


class TestCoordinateNormalizationPerformance:
    """测试坐标归一化还原的性能。"""

    def test_single_conversion_performance(self):
        """测试: 单个bbox转换时间应小于1微秒。"""
        # 执行10000次转换取平均
        number = 10000
        total_time = timeit.timeit(
            stmt=lambda: VisualLocator._denormalize_bbox((500, 500, 600, 600), (1920, 1080)),
            number=number,
        )

        avg_time = total_time / number
        print(f"\n单次转换平均时间: {avg_time * 1_000_000:.2f} 微秒")

        # 验证单次转换 < 1微秒
        assert avg_time < 1e-6, f"单次转换时间 {avg_time} 超过1微秒"

    def test_detection_performance(self):
        """测试: 坐标检测时间性能。"""
        number = 10000
        total_time = timeit.timeit(
            stmt=lambda: VisualLocator._is_normalized_coordinate((100, 200, 300, 400), (1920, 1080)),
            number=number,
        )

        avg_time = total_time / number
        print(f"\n单次检测平均时间: {avg_time * 1_000_000:.2f} 微秒")

        # 验证检测时间 < 1微秒
        assert avg_time < 1e-6, f"单次检测时间 {avg_time} 超过1微秒"

    def test_batch_conversion_performance(self):
        """测试: 批量转换100个bbox的时间。"""
        # 准备100个bbox
        bboxes = [(i * 10, i * 10, (i + 1) * 10, (i + 1) * 10) for i in range(100)]

        def batch_convert():
            for bbox in bboxes:
                VisualLocator._denormalize_bbox(bbox, (1920, 1080))

        number = 100
        total_time = timeit.timeit(stmt=batch_convert, number=number)

        avg_batch_time = total_time / number
        avg_per_bbox = avg_batch_time / len(bboxes)

        print(f"\n批量转换100个bbox平均时间: {avg_batch_time * 1_000:.2f} 毫秒")
        print(f"平均每个bbox: {avg_per_bbox * 1_000_000:.2f} 微秒")

        # 验证批量转换时间合理
        assert avg_batch_time < 0.1, f"批量转换100个bbox时间 {avg_batch_time} 超过100毫秒"
        assert avg_per_bbox < 1e-6, f"平均每个bbox转换时间 {avg_per_bbox} 超过1微秒"

    def test_combined_detection_and_conversion(self):
        """测试: 检测+转换组合操作的性能。"""
        def combined_operation():
            bbox = (100, 200, 300, 400)
            image_size = (1920, 1080)
            if VisualLocator._is_normalized_coordinate(bbox, image_size):
                VisualLocator._denormalize_bbox(bbox, image_size)

        number = 10000
        total_time = timeit.timeit(stmt=combined_operation, number=number)

        avg_time = total_time / number
        print(f"\n检测+转换组合操作平均时间: {avg_time * 1_000_000:.2f} 微秒")

        # 验证组合操作时间 < 2微秒
        assert avg_time < 2e-6, f"组合操作时间 {avg_time} 超过2微秒"

    def test_performance_comparison_normalized_vs_pixel(self):
        """测试: 对比归一化坐标和像素坐标的性能差异。"""
        number = 10000

        # 归一化坐标(需要检测+转换)
        normalized_time = timeit.timeit(
            stmt=lambda: VisualLocator._is_normalized_coordinate((100, 200, 300, 400), (1920, 1080))
            and VisualLocator._denormalize_bbox((100, 200, 300, 400), (1920, 1080)),
            number=number,
        )

        # 像素坐标(只需要检测,不转换)
        pixel_time = timeit.timeit(
            stmt=lambda: VisualLocator._is_normalized_coordinate((500, 600, 700, 800), (800, 600)),
            number=number,
        )

        avg_normalized = normalized_time / number
        avg_pixel = pixel_time / number
        overhead = avg_normalized - avg_pixel

        print(f"\n归一化坐标平均时间: {avg_normalized * 1_000_000:.2f} 微秒")
        print(f"像素坐标平均时间: {avg_pixel * 1_000_000:.2f} 微秒")
        print(f"性能开销: {overhead * 1_000_000:.2f} 微秒")

        # 验证开销可接受
        assert overhead < 1e-6, f"性能开销 {overhead} 超过1微秒"

    def test_different_resolution_performance(self):
        """测试: 不同分辨率下的转换性能。"""
        resolutions = [
            (1920, 1080),  # Full HD
            (2560, 1440),  # 2K
            (3840, 2160),  # 4K
            (1280, 720),  # HD
        ]

        results = {}
        for resolution in resolutions:
            time_taken = timeit.timeit(
                stmt=lambda r=resolution: VisualLocator._denormalize_bbox((500, 500, 600, 600), r),
                number=10000,
            )
            avg_time = (time_taken / 10000) * 1_000_000
            results[resolution] = avg_time
            print(f"{resolution}: 平均 {avg_time:.2f} 微秒")

        # 验证所有分辨率下性能都达标
        for resolution, avg_time in results.items():
            assert avg_time < 1.0, f"分辨率 {resolution} 下转换时间 {avg_time} 微秒超过1微秒"
