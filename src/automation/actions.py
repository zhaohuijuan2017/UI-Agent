"""操作类型定义。"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ActionType(Enum):
    """操作类型枚举。"""

    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    DRAG = "drag"
    TYPE = "type"
    SHORTCUT = "shortcut"
    WAIT = "wait"
    WAIT_FOR_DIALOG = "wait_for_dialog"


@dataclass
class Action:
    """单个操作。

    Attributes:
        type: 操作类型
        target: 目标元素名称
        parameters: 操作参数
        timeout: 超时时间（秒）
        retry: 重试次数
    """

    type: ActionType
    target: str | None = None
    parameters: dict[str, Any] | None = None
    timeout: float = 5.0
    retry: int = 3
