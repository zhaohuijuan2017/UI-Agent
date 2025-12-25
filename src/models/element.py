"""UI 元素相关的数据模型。"""

from dataclasses import dataclass
from typing import Any


@dataclass
class UIElement:
    """UI 元素信息。

    Attributes:
        element_type: 元素类型（button, menu, text_field, tree 等）
        description: 元素描述
        bbox: 边界框 (x1, y1, x2, y2)
        confidence: 定位置信度 (0-1)
        metadata: 额外的元数据
    """

    element_type: str
    description: str
    bbox: tuple[int, int, int, int]
    confidence: float
    metadata: dict[str, Any] | None = None

    @property
    def center(self) -> tuple[int, int]:
        """计算元素中心点坐标。"""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)

    @property
    def width(self) -> int:
        """元素宽度。"""
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> int:
        """元素高度。"""
        return self.bbox[3] - self.bbox[1]
