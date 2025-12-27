"""工作流异常类。"""


class WorkflowError(Exception):
    """工作流基础异常。"""

    pass


class WorkflowParseError(WorkflowError):
    """工作流文档解析错误。"""

    def __init__(self, message: str, line_number: int | None = None) -> None:
        """初始化解析错误。

        Args:
            message: 错误信息
            line_number: 错误所在行号（可选）
        """
        self.line_number = line_number
        if line_number is not None:
            message = f"第 {line_number} 行: {message}"
        super().__init__(message)


class WorkflowExecutionError(WorkflowError):
    """工作流执行错误。"""

    def __init__(self, message: str, step_index: int | None = None) -> None:
        """初始化执行错误。

        Args:
            message: 错误信息
            step_index: 失败的步骤索引（可选）
        """
        self.step_index = step_index
        if step_index is not None:
            message = f"步骤 {step_index + 1}: {message}"
        super().__init__(message)


class WorkflowValidationError(WorkflowError):
    """工作流验证错误。"""

    def __init__(self, errors: list[str]) -> None:
        """初始化验证错误。

        Args:
            errors: 错误列表
        """
        self.errors = errors
        message = "工作流验证失败:\n" + "\n".join(f"  - {e}" for e in errors)
        super().__init__(message)
