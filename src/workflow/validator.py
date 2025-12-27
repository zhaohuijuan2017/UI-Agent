"""工作流验证器。"""

from src.workflow.models import WorkflowConfig, WorkflowStep


class WorkflowValidator:
    """工作流验证器。"""

    def __init__(self, available_operations: set[str] | None = None) -> None:
        """初始化验证器。

        Args:
            available_operations: 可用的操作名称集合
        """
        self.available_operations = available_operations or set()

    def validate(self, config: WorkflowConfig) -> list[str]:
        """验证工作流配置。

        Args:
            config: 工作流配置

        Returns:
            错误列表（空列表表示验证通过）
        """
        errors = []

        # 验证名称
        if not config.name or not config.name.strip():
            errors.append("工作流名称不能为空")

        # 验证步骤
        if not config.steps:
            errors.append("工作流必须包含至少一个步骤")

        for i, step in enumerate(config.steps):
            step_errors = self._validate_step(step, i)
            errors.extend(step_errors)

        return errors

    def _validate_step(self, step: WorkflowStep, index: int) -> list[str]:
        """验证单个步骤。

        Args:
            step: 步骤对象
            index: 步骤索引

        Returns:
            错误列表
        """
        errors = []
        prefix = f"步骤 {index + 1}"

        # 验证描述
        if not step.description or not step.description.strip():
            errors.append(f"{prefix}: 步骤描述不能为空")

        # 验证操作名称
        if step.operation:
            if self.available_operations and step.operation not in self.available_operations:
                errors.append(
                    f"{prefix}: 未知的操作 '{step.operation}'。"
                    f"可用操作: {', '.join(sorted(self.available_operations))}"
                )

        # 验证重试配置
        if step.retry_count < 0:
            errors.append(f"{prefix}: 重试次数不能为负数")

        if step.retry_interval < 0:
            errors.append(f"{prefix}: 重试间隔不能为负数")

        # 验证条件表达式
        if step.condition:
            if not self._is_valid_condition(step.condition):
                errors.append(
                    f"{prefix}: 无效的条件表达式 '{step.condition}'。"
                    "支持的格式: if_success, if_failure"
                )

        return errors

    def _is_valid_condition(self, condition: str) -> bool:
        """检查条件表达式是否有效。

        Args:
            condition: 条件表达式

        Returns:
            是否有效
        """
        condition = condition.strip()
        valid_conditions = ["if_success", "if_failure"]
        return condition in valid_conditions or condition.startswith("if ")
