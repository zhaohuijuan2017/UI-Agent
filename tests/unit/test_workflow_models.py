"""工作流数据模型单元测试。"""

import pytest

from src.workflow.models import (
    StepResult,
    WorkflowConfig,
    WorkflowResult,
    WorkflowStep,
)


@pytest.mark.unit
class TestWorkflowStep:
    """工作流步骤测试。"""

    def test_create_step_minimal(self):
        """测试创建最小步骤。"""
        step = WorkflowStep(description="打开文件")
        assert step.description == "打开文件"
        assert step.operation is None
        assert step.retry_count == 0
        assert step.retry_interval == 1.0
        assert step.condition is None
        assert step.continue_on_error is False

    def test_create_step_full(self):
        """测试创建完整步骤。"""
        step = WorkflowStep(
            description="打开文件",
            operation="double_click_file",
            parameters={"filename": "main.py"},
            retry_count=3,
            retry_interval=2.0,
            condition="if_success",
            continue_on_error=True,
        )
        assert step.description == "打开文件"
        assert step.operation == "double_click_file"
        assert step.parameters["filename"] == "main.py"
        assert step.retry_count == 3
        assert step.retry_interval == 2.0
        assert step.condition == "if_success"
        assert step.continue_on_error is True


@pytest.mark.unit
class TestWorkflowConfig:
    """工作流配置测试。"""

    def test_create_config_minimal(self):
        """测试创建最小配置。"""
        config = WorkflowConfig(name="测试工作流")
        assert config.name == "测试工作流"
        assert config.description == ""
        assert config.steps == []
        assert config.variables == {}

    def test_create_config_full(self):
        """测试创建完整配置。"""
        step = WorkflowStep(description="步骤1")
        config = WorkflowConfig(
            name="测试工作流",
            description="这是一个测试",
            steps=[step],
            variables={"url": "https://example.com"},
        )
        assert config.name == "测试工作流"
        assert config.description == "这是一个测试"
        assert len(config.steps) == 1
        assert config.variables["url"] == "https://example.com"


@pytest.mark.unit
class TestStepResult:
    """步骤结果测试。"""

    def test_create_result_success(self):
        """测试创建成功结果。"""
        result = StepResult(
            step_index=0,
            description="步骤1",
            success=True,
        )
        assert result.step_index == 0
        assert result.description == "步骤1"
        assert result.success is True
        assert result.skipped is False
        assert result.error_message is None

    def test_create_result_failure(self):
        """测试创建失败结果。"""
        result = StepResult(
            step_index=0,
            description="步骤1",
            success=False,
            error_message="执行失败",
            retry_count=2,
        )
        assert result.success is False
        assert result.error_message == "执行失败"
        assert result.retry_count == 2

    def test_create_result_skipped(self):
        """测试创建跳过结果。"""
        result = StepResult(
            step_index=1,
            description="步骤2",
            success=True,
            skipped=True,
        )
        assert result.skipped is True


@pytest.mark.unit
class TestWorkflowResult:
    """工作流结果测试。"""

    def test_create_result_success(self):
        """测试创建成功的工作流结果。"""
        step_result = StepResult(step_index=0, description="步骤1", success=True)
        result = WorkflowResult(
            workflow_name="测试工作流",
            success=True,
            completed_steps=1,
            total_steps=1,
            step_results=[step_result],
        )
        assert result.workflow_name == "测试工作流"
        assert result.success is True
        assert result.completed_steps == 1
        assert result.total_steps == 1
        assert len(result.step_results) == 1
        assert result.failed_step is None

    def test_create_result_failure(self):
        """测试创建失败的工作流结果。"""
        step_result = StepResult(
            step_index=0, description="步骤1", success=False, error_message="错误"
        )
        result = WorkflowResult(
            workflow_name="测试工作流",
            success=False,
            completed_steps=1,
            total_steps=2,
            failed_step=0,
            error_message="步骤执行失败",
            step_results=[step_result],
        )
        assert result.success is False
        assert result.failed_step == 0
        assert result.error_message == "步骤执行失败"
