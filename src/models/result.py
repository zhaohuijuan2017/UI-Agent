"""执行结果相关的数据模型。"""

from dataclasses import dataclass
from enum import Enum


class ExecutionStatus(Enum):
    """执行状态枚举。"""

    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class ExecutionResult:
    """命令执行结果。

    Attributes:
        status: 执行状态
        message: 结果消息
        error: 错误信息（如果有）
        data: 附加数据
        duration_ms: 执行耗时（毫秒）
    """

    status: ExecutionStatus
    message: str
    error: str | None = None
    data: dict | None = None
    duration_ms: int = 0

    @property
    def success(self) -> bool:
        """是否执行成功。"""
        return self.status == ExecutionStatus.SUCCESS
