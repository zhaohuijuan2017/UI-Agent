"""命令解析相关的数据模型。"""

from dataclasses import dataclass
from typing import Any


@dataclass
class ParsedCommand:
    """解析后的命令结构。

    Attributes:
        intent: 意图类型（如 file_operation, refactor, navigation）
        action: 具体操作（如 open_file, rename_symbol）
        parameters: 提取的参数字典
        confidence: 解析置信度 (0-1)
        context: 上下文信息
    """

    intent: str
    action: str
    parameters: dict[str, Any]
    confidence: float
    context: dict[str, Any]

    def validate(self) -> bool:
        """验证命令有效性。

        Returns:
            命令是否有效
        """
        return bool(self.intent and self.action and self.confidence > 0.5)
