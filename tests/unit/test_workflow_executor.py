"""工作流执行器单元测试。"""

from unittest.mock import MagicMock, Mock

import pytest

from src.workflow.executor import WorkflowExecutor
from src.workflow.models import (
    WorkflowConfig,
    WorkflowStep,
)


class MockExecutionResult:
    """模拟执行结果。"""

    def __init__(self, status: str = "success", error: str | None = None, message: str = ""):
        self.status = Mock(value=status)
        self.error = error
        self.message = message


@pytest.mark.unit
class TestWorkflowExecutor:
    """工作流执行器测试。"""

    @pytest.fixture
    def mock_ide_controller(self):
        """创建模拟 IDE 控制器。"""
        controller = MagicMock()
        controller.execute_command = MagicMock(return_value=MockExecutionResult("success"))
        return controller

    @pytest.fixture
    def executor(self, mock_ide_controller):
        """创建执行器实例。"""
        return WorkflowExecutor(mock_ide_controller)

    def test_execute_simple_workflow(self, executor):
        """测试执行简单工作流。"""
        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(description="步骤1"),
                WorkflowStep(description="步骤2"),
            ],
        )

        result = executor.execute(config)

        assert result.success is True
        assert result.completed_steps == 2
        assert result.total_steps == 2
        assert len(result.step_results) == 2

    def test_execute_workflow_with_failure(self, executor, mock_ide_controller):
        """测试执行失败的工作流。"""
        # 模拟第二步失败
        mock_ide_controller.execute_command.side_effect = [
            MockExecutionResult("success"),
            MockExecutionResult("error", error="执行失败"),
        ]

        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(description="步骤1"),
                WorkflowStep(description="步骤2"),
                WorkflowStep(description="步骤3"),
            ],
        )

        result = executor.execute(config)

        assert result.success is False
        assert result.completed_steps == 2
        assert result.failed_step == 1
        assert result.error_message is not None

    def test_execute_workflow_with_continue_on_error(self, executor, mock_ide_controller):
        """测试失败继续执行的工作流。"""
        # 模拟第二步失败
        mock_ide_controller.execute_command.side_effect = [
            MockExecutionResult("success"),
            MockExecutionResult("error", error="执行失败"),
            MockExecutionResult("success"),
        ]

        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(description="步骤1"),
                WorkflowStep(description="步骤2", continue_on_error=True),
                WorkflowStep(description="步骤3"),
            ],
        )

        result = executor.execute(config)

        # 应该执行完所有步骤
        assert result.completed_steps == 3
        assert len(result.step_results) == 3
        # 第二步应该失败
        assert result.step_results[1].success is False
        # 第三步应该成功
        assert result.step_results[2].success is True

    def test_execute_workflow_with_retry(self, executor, mock_ide_controller):
        """测试带重试的工作流执行。"""
        # 模拟前两次失败，第三次成功
        mock_ide_controller.execute_command.side_effect = [
            MockExecutionResult("error", error="失败1"),
            MockExecutionResult("error", error="失败2"),
            MockExecutionResult("success"),
        ]

        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(description="步骤1", retry_count=2, retry_interval=0.1),
            ],
        )

        result = executor.execute(config)

        assert result.success is True
        assert result.step_results[0].retry_count == 2

    def test_execute_workflow_exhaust_retries(self, executor, mock_ide_controller):
        """测试重试次数用尽的情况。"""
        # 模拟所有尝试都失败
        mock_ide_controller.execute_command.return_value = MockExecutionResult(
            "error", error="持续失败"
        )

        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(description="步骤1", retry_count=2, retry_interval=0.1),
            ],
        )

        result = executor.execute(config)

        assert result.success is False
        assert result.step_results[0].retry_count == 2

    def test_condition_if_success(self, executor, mock_ide_controller):
        """测试 if_success 条件。"""
        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(description="步骤1"),
                WorkflowStep(description="步骤2", condition="if_success"),
            ],
        )

        result = executor.execute(config)

        # 第二步应该执行
        assert result.completed_steps == 2
        assert result.step_results[1].skipped is False

    def test_condition_if_failure(self, executor, mock_ide_controller):
        """测试 if_failure 条件。"""
        # 模拟第一步失败，然后第二步和第三步也失败
        mock_ide_controller.execute_command.side_effect = [
            MockExecutionResult("error", error="失败"),
            MockExecutionResult("success"),  # 错误处理步骤成功
            MockExecutionResult("error", error="失败"),  # 但正常步骤因为条件问题失败
        ]

        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                # 第一步失败但继续执行
                WorkflowStep(description="步骤1", continue_on_error=True),
                # 第二步因上一步失败而执行（if_failure）
                WorkflowStep(description="错误处理", condition="if_failure"),
                # 第三步 - 无条件步骤，会执行
                WorkflowStep(description="清理步骤"),
            ],
        )

        result = executor.execute(config)

        # 第二步应该执行（因为第一步失败）
        assert result.step_results[1].skipped is False
        # 第三步应该执行（无条件）
        assert result.step_results[2].skipped is False

    def test_dry_run_mode(self, executor):
        """测试 dry-run 模式。"""
        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(description="步骤1"),
                WorkflowStep(description="步骤2", operation="open_file"),
            ],
        )

        result = executor.execute(config, dry_run=True)

        # dry-run 模式下应该成功
        assert result.success is True
        # 所有步骤都应该被标记为成功
        assert all(r.success for r in result.step_results)

    def test_dry_run_with_yaml_config(self, executor):
        """测试 dry-run 模式下的 YAML 配置验证。"""
        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(
                    description="步骤1",
                    operation="double_click_file",
                    parameters={"filename": "test.py"},
                    retry_count=3,
                    retry_interval=2.0,
                    condition="if_success",
                    continue_on_error=True,
                ),
            ],
        )

        result = executor.execute(config, dry_run=True)

        assert result.success is True

    def test_execute_workflow_with_operation(self, executor, mock_ide_controller):
        """测试指定操作名称的执行。"""
        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(
                    description="双击文件",
                    operation="double_click_file",
                    parameters={"filename": "main.py"},
                ),
            ],
        )

        result = executor.execute(config)

        assert result.success is True
        # 验证 IDE 控制器被正确调用
        mock_ide_controller.execute_command.assert_called_once()

    def test_execute_workflow_with_template(self, executor, mock_ide_controller):
        """测试带模板参数的执行。"""
        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(
                    description="点击运行按钮",
                    operation="click_button",
                    parameters={"template": "run_button.png"},
                ),
            ],
        )

        result = executor.execute(config)

        assert result.success is True
        # 验证传递了 template 参数
        mock_ide_controller.execute_command.assert_called_once()
        call_kwargs = mock_ide_controller.execute_command.call_args.kwargs
        assert "template_name" in call_kwargs
        assert call_kwargs["template_name"] == "run_button.png"

    def test_step_result_duration(self, executor):
        """测试步骤执行时长记录。"""
        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(description="步骤1"),
            ],
        )

        result = executor.execute(config)

        # 应该记录了执行时长
        assert result.step_results[0].duration >= 0

    def test_workflow_result_duration(self, executor):
        """测试工作流总执行时长记录。"""
        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(description="步骤1"),
                WorkflowStep(description="步骤2"),
            ],
        )

        result = executor.execute(config)

        # 应该记录了总执行时长
        assert result.duration >= 0

    def test_empty_workflow(self, executor):
        """测试空工作流。"""
        config = WorkflowConfig(name="空工作流", steps=[])

        result = executor.execute(config)

        # 空工作流应该成功
        assert result.success is True
        assert result.completed_steps == 0

    def test_first_step_always_executes(self, executor):
        """测试第一步总是执行（即使有条件）。"""
        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(description="第一步", condition="if_success"),
            ],
        )

        result = executor.execute(config)

        # 第一步应该执行（忽略条件）
        assert result.completed_steps == 1
        assert result.step_results[0].skipped is False

    def test_no_condition_always_executes(self, executor):
        """测试无条件步骤总是执行。"""
        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(description="步骤1"),
                WorkflowStep(description="步骤2"),  # 无条件
            ],
        )

        result = executor.execute(config, dry_run=True)

        assert result.completed_steps == 2

    def test_step_with_exception(self, executor, mock_ide_controller):
        """测试步骤执行异常情况。"""
        # 模拟抛出异常
        mock_ide_controller.execute_command.side_effect = Exception("异常错误")

        config = WorkflowConfig(
            name="测试工作流",
            steps=[
                WorkflowStep(description="步骤1", retry_count=1),
            ],
        )

        result = executor.execute(config)

        assert result.success is False
        assert result.error_message is not None
