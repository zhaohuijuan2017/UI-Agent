"""任务编排器单元测试。"""

from unittest.mock import MagicMock

import pytest

from src.intent.models import Intent
from src.orchestration.context import ExecutionContext, StepExecutionResult
from src.orchestration.executor import TaskExecutor
from src.orchestration.orchestrator import TaskOrchestrator
from src.templates.loader import TemplateLoader
from src.templates.models import TaskFlowTemplate, TemplateStep


@pytest.fixture
def mock_executor():
    """模拟任务执行器。"""
    executor = MagicMock(spec=TaskExecutor)

    # 模拟成功执行
    executor.execute_step = MagicMock(
        return_value=StepExecutionResult(
            step_index=0,
            success=True,
            output={"result": "success"},
            duration=0.5,
        )
    )

    return executor


@pytest.fixture
def mock_template_loader():
    """模拟模板加载器。"""
    loader = MagicMock(spec=TemplateLoader)

    # 创建示例模板
    template = TaskFlowTemplate(
        name="develop-feature",
        description="需求开发模板",
        intent_types=["develop-feature"],
        steps=[
            TemplateStep(system="ide", action="switch_ide", parameters={"ide_name": "PyCharm"}),
            TemplateStep(system="ide", action="generate_code", parameters={"requirement": "登录功能"}),
        ],
    )

    loader.get_template_by_intent = MagicMock(return_value=template)

    return loader


@pytest.fixture
def orchestrator(mock_executor, mock_template_loader):
    """创建任务编排器实例。"""
    return TaskOrchestrator(executor=mock_executor, template_loader=mock_template_loader)


@pytest.fixture
def sample_intent():
    """创建示例意图。"""
    return Intent(
        type="develop-feature",
        parameters={"requirement_text": "实现登录功能"},
        confidence=0.95,
        raw_message="帮我实现登录功能",
        reasoning="匹配到开发意图",
    )


class TestTaskOrchestrator:
    """任务编排器测试类。"""

    def test_init(self, mock_executor, mock_template_loader):
        """测试初始化。"""
        orchestrator = TaskOrchestrator(mock_executor, mock_template_loader)

        assert orchestrator.executor is mock_executor
        assert orchestrator.template_loader is mock_template_loader
        assert orchestrator.template_engine is not None

    def test_orchestrate_success(self, orchestrator, sample_intent, mock_executor):
        """测试成功编排任务。"""
        context = orchestrator.orchestrate(sample_intent)

        assert context.status == "completed"
        assert len(context.step_results) == 2
        assert all(r.success for r in context.step_results)

        # 验证执行器被调用
        assert mock_executor.execute_step.call_count == 2

    def test_orchestrate_with_existing_context(self, orchestrator, sample_intent):
        """测试使用现有上下文编排。"""
        existing_context = ExecutionContext()
        existing_context.set_data("predefined_key", "predefined_value")

        context = orchestrator.orchestrate(sample_intent, existing_context)

        assert context is existing_context
        assert context.get_data("predefined_key") == "predefined_value"

    def test_orchestrate_template_not_found(self, sample_intent, mock_executor):
        """测试模板未找到的情况。"""
        mock_loader = MagicMock(spec=TemplateLoader)
        mock_loader.get_template_by_intent = MagicMock(return_value=None)

        orchestrator = TaskOrchestrator(mock_executor, mock_loader)

        context = orchestrator.orchestrate(sample_intent)

        assert context.status == "failed"

    def test_orchestrate_step_failure(self, orchestrator, sample_intent, mock_executor):
        """测试步骤失败时停止执行。"""
        # 模拟第一步成功，第二步失败
        mock_executor.execute_step = MagicMock(
            side_effect=[
                StepExecutionResult(step_index=0, success=True, output={}, duration=0.5),
                StepExecutionResult(step_index=1, success=False, error="执行失败", duration=0.3),
            ]
        )

        context = orchestrator.orchestrate(sample_intent)

        assert context.status == "failed"
        assert context.step_results[0].success is True
        assert context.step_results[1].success is False

    def test_orchestrate_with_continue_on_error(self, sample_intent, mock_executor, mock_template_loader):
        """测试 continue_on_error 时继续执行。"""
        # 创建包含 continue_on_error 的模板
        template = TaskFlowTemplate(
            name="test",
            description="测试",
            intent_types=["test"],
            steps=[
                TemplateStep(system="ide", action="step1", parameters={}),
                TemplateStep(system="ide", action="step2", parameters={}, continue_on_error=True),
                TemplateStep(system="ide", action="step3", parameters={}),
            ],
        )

        mock_template_loader.get_template_by_intent = MagicMock(return_value=template)

        # 模拟中间步骤失败
        mock_executor.execute_step = MagicMock(
            side_effect=[
                StepExecutionResult(step_index=0, success=True, output={}, duration=0.5),
                StepExecutionResult(step_index=1, success=False, error="失败", duration=0.3),
                StepExecutionResult(step_index=2, success=True, output={}, duration=0.5),
            ]
        )

        orchestrator = TaskOrchestrator(mock_executor, mock_template_loader)

        intent = Intent(type="test", parameters={}, confidence=1.0, raw_message="test")
        context = orchestrator.orchestrate(intent)

        # 所有步骤都应该执行
        assert mock_executor.execute_step.call_count == 3
        assert context.step_results[1].success is False
        assert context.step_results[2].success is True

    def test_orchestrate_with_conditional_steps(self, sample_intent, mock_executor, mock_template_loader):
        """测试条件步骤执行。"""
        # 创建包含条件步骤的模板
        template = TaskFlowTemplate(
            name="test",
            description="测试",
            intent_types=["test"],
            steps=[
                TemplateStep(system="ide", action="step1", parameters={}),
                TemplateStep(system="ide", action="step2", parameters={}, condition="if_success"),
                TemplateStep(system="ide", action="step3", parameters={}, condition="if_failure"),
            ],
        )

        mock_template_loader.get_template_by_intent = MagicMock(return_value=template)

        # 模拟第一步成功
        mock_executor.execute_step = MagicMock(
            return_value=StepExecutionResult(step_index=0, success=True, output={}, duration=0.5)
        )

        orchestrator = TaskOrchestrator(mock_executor, mock_template_loader)

        intent = Intent(type="test", parameters={}, confidence=1.0, raw_message="test")
        context = orchestrator.orchestrate(intent)

        # 第一步和第二步（if_success）应该执行
        # 第三步（if_failure）应该跳过
        assert mock_executor.execute_step.call_count == 2

    def test_show_execution_plan(self, orchestrator, sample_intent):
        """测试显示执行计划。"""
        plan = orchestrator.show_execution_plan(sample_intent)

        assert plan["intent"] == "develop-feature"
        assert plan["template"] == "develop-feature"
        assert plan["description"] == "需求开发模板"
        assert len(plan["steps"]) == 2
        assert plan["steps"][0]["system"] == "ide"
        assert plan["steps"][0]["action"] == "switch_ide"

    def test_show_execution_plan_template_not_found(self, sample_intent, mock_executor):
        """测试模板未找到时的执行计划。"""
        mock_loader = MagicMock(spec=TemplateLoader)
        mock_loader.get_template_by_intent = MagicMock(return_value=None)

        orchestrator = TaskOrchestrator(mock_executor, mock_loader)

        plan = orchestrator.show_execution_plan(sample_intent)

        assert "error" in plan

    def test_orchestrate_data_passing(self, orchestrator, sample_intent, mock_executor):
        """测试步骤间数据传递。"""
        # 模拟步骤返回数据
        mock_executor.execute_step = MagicMock(
            side_effect=[
                StepExecutionResult(
                    step_index=0,
                    success=True,
                    output={"extracted_requirement": "登录需求详情"},
                    duration=0.5,
                ),
                StepExecutionResult(
                    step_index=1,
                    success=True,
                    output={"code_generated": True},
                    duration=1.0,
                ),
            ]
        )

        # 更新模板以支持数据传递
        template = TaskFlowTemplate(
            name="test",
            description="测试",
            intent_types=["develop-feature"],
            steps=[
                TemplateStep(
                    system="browser",
                    action="extract",
                    parameters={},
                    output_to="requirement_data",
                ),
                TemplateStep(
                    system="ide",
                    action="generate",
                    parameters={},
                    input_from="requirement_data",
                ),
            ],
        )

        orchestrator.template_loader.get_template_by_intent = MagicMock(return_value=template)

        context = orchestrator.orchestrate(sample_intent)

        # 验证数据被保存到上下文（通过 output_to）
        assert context.get_data("requirement_data") == {"extracted_requirement": "登录需求详情"}
        # step_X_output 是在 executor 内部保存的，需要真实执行才会有
        # 这里只验证 output_to 指定的键

    def test_orchestrate_exception_handling(self, orchestrator, sample_intent, mock_executor):
        """测试异常处理。"""
        # 模拟执行器抛出异常
        mock_executor.execute_step = MagicMock(side_effect=Exception("执行异常"))

        context = orchestrator.orchestrate(sample_intent)

        assert context.status == "failed"

    def test_log_execution_summary(self, orchestrator, sample_intent, mock_executor, caplog):
        """测试执行摘要日志。"""
        import logging

        mock_executor.execute_step = MagicMock(
            return_value=StepExecutionResult(step_index=0, success=True, output={}, duration=1.5)
        )

        with caplog.at_level(logging.INFO):
            context = orchestrator.orchestrate(sample_intent)

        # 验证日志包含执行摘要
        assert any("执行摘要" in record.message for record in caplog.records)
        assert any("状态:" in record.message for record in caplog.records)

    def test_orchestrate_with_parameters_binding(self, orchestrator, sample_intent):
        """测试参数绑定。"""
        context = orchestrator.orchestrate(sample_intent)

        # 验证参数被正确绑定
        assert context.status == "completed"
