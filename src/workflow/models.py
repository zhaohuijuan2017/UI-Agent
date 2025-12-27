"""工作流数据模型。"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowStep:
    """工作流步骤模型。"""

    description: str  # 步骤描述（自然语言）
    operation: str | None = None  # 操作名称（从描述解析或显式指定）
    parameters: dict[str, Any] = field(default_factory=dict)  # 操作参数
    retry_count: int = 0  # 重试次数
    retry_interval: float = 1.0  # 重试间隔（秒）
    condition: str | None = None  # 执行条件
    continue_on_error: bool = False  # 失败时是否继续


@dataclass
class WorkflowConfig:
    """工作流配置模型。"""

    name: str  # 工作流名称
    description: str = ""  # 工作流描述
    steps: list[WorkflowStep] = field(default_factory=list)  # 步骤列表
    variables: dict[str, Any] = field(default_factory=dict)  # 变量字典
    metadata: dict[str, Any] = field(default_factory=dict)  # 其他元数据


@dataclass
class StepResult:
    """步骤执行结果。"""

    step_index: int  # 步骤索引
    description: str  # 步骤描述
    success: bool  # 是否成功
    skipped: bool = False  # 是否被跳过
    error_message: str | None = None  # 错误信息
    retry_count: int = 0  # 实际重试次数
    duration: float = 0.0  # 执行时长


@dataclass
class WorkflowResult:
    """工作流执行结果。"""

    workflow_name: str  # 工作流名称
    success: bool  # 整体是否成功
    completed_steps: int  # 完成的步骤数
    total_steps: int  # 总步骤数
    failed_step: int | None = None  # 失败的步骤索引
    error_message: str | None = None  # 错误信息
    step_results: list[StepResult] = field(default_factory=list)  # 每步结果
    duration: float = 0.0  # 总执行时长
