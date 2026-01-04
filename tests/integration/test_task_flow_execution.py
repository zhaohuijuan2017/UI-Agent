"""任务流执行集成测试。"""

from unittest.mock import MagicMock

import pytest

from src.intent.models import Intent
from src.orchestration.adapters import SystemAdapter
from src.orchestration.context import ExecutionContext, StepExecutionResult
from src.orchestration.executor import TaskExecutor
from src.orchestration.orchestrator import TaskOrchestrator
from src.templates.loader import TemplateLoader
from src.templates.models import TaskFlowTemplate, TemplateStep


class MockSystemAdapter(SystemAdapter):
    """模拟系统适配器。"""

    def __init__(self, system_name: str):
        self.system_name = system_name
        self.executed_actions = []

    def execute(self, action: str, parameters: dict) -> StepExecutionResult:
        """执行动作并记录。"""
        self.executed_actions.append((action, parameters))

        # 模拟成功执行
        return StepExecutionResult(
            step_index=0,
            success=True,
            output={"action": action, "params": parameters},
            duration=0.1,
        )


@pytest.fixture
def mock_browser_adapter():
    """模拟浏览器适配器。"""
    return MockSystemAdapter("browser")


@pytest.fixture
def mock_ide_adapter():
    """模拟 IDE 适配器。"""
    return MockSystemAdapter("ide")


@pytest.fixture
def task_executor(mock_browser_adapter, mock_ide_adapter):
    """创建任务执行器。"""
    executor = TaskExecutor()
    executor.register_adapter("browser", mock_browser_adapter)
    executor.register_adapter("ide", mock_ide_adapter)
    return executor


@pytest.fixture
def template_loader():
    """创建模板加载器。"""
    loader = TemplateLoader()

    # 注册测试模板
    template = TaskFlowTemplate(
        name="develop-feature",
        description="需求开发模板",
        intent_types=["develop-feature"],
        steps=[
            TemplateStep(system="ide", action="switch_ide", parameters={"ide_name": "PyCharm"}),
            TemplateStep(system="ide", action="activate_plugin", parameters={"plugin_name": "ai-assistant"}),
            TemplateStep(system="ide", action="generate_code", parameters={"requirement": "{{intent.requirement_text}}"}),
        ],
    )
    loader.register_template(template)

    # 注册跨系统模板
    cross_system_template = TaskFlowTemplate(
        name="requirement-to-development",
        description="需求查看并开发",
        intent_types=["requirement-to-development"],
        steps=[
            TemplateStep(
                system="browser",
                action="open_url",
                parameters={"url": "{{intent.url}}"},
                output_to="page_content",
            ),
            TemplateStep(
                system="browser",
                action="extract_requirement",
                parameters={},
                input_from="page_content",
                output_to="requirement_data",
            ),
            TemplateStep(
                system="ide",
                action="switch_ide",
                parameters={"ide_name": "PyCharm"},
            ),
            TemplateStep(
                system="ide",
                action="generate_code",
                parameters={"requirement": "{{intent.requirement_text}}"},
                input_from="requirement_data",
            ),
        ],
    )
    loader.register_template(cross_system_template)

    return loader


@pytest.fixture
def task_orchestrator(task_executor, template_loader):
    """创建任务编排器。"""
    return TaskOrchestrator(task_executor, template_loader)


class TestTaskFlowExecution:
    """任务流执行集成测试类。"""

    def test_single_system_task_flow(self, task_orchestrator, task_executor):
        """测试单系统任务流执行。"""
        intent = Intent(
            type="develop-feature",
            parameters={"requirement_text": "实现用户登录功能"},
            confidence=0.95,
            raw_message="帮我实现用户登录功能",
        )

        context = task_orchestrator.orchestrate(intent)

        assert context.status == "completed"
        assert len(context.step_results) == 3
        assert all(r.success for r in context.step_results)

    def test_cross_system_task_flow(self, task_orchestrator, task_executor, mock_browser_adapter, mock_ide_adapter):
        """测试跨系统任务流执行。"""
        intent = Intent(
            type="requirement-to-development",
            parameters={
                "url": "https://github.com/user/repo/issues/1",
                "requirement_text": "实现登录功能",
            },
            confidence=0.90,
            raw_message="帮我查看这个需求并实现",
        )

        context = task_orchestrator.orchestrate(intent)

        assert context.status == "completed"
        assert len(context.step_results) == 4

        # 验证浏览器和 IDE 都被调用
        assert len(mock_browser_adapter.executed_actions) == 2
        assert len(mock_ide_adapter.executed_actions) == 2

    def test_data_flow_between_steps(self, task_orchestrator):
        """测试步骤间数据流转。"""
        intent = Intent(
            type="requirement-to-development",
            parameters={
                "url": "https://github.com/user/repo/issues/1",
                "requirement_text": "实现登录功能",
            },
            confidence=0.90,
            raw_message="查看需求并实现",
        )

        context = task_orchestrator.orchestrate(intent)

        # 验证数据被正确传递
        assert "page_content" in context.shared_data
        assert "requirement_data" in context.shared_data

    def test_execution_report(self, task_orchestrator):
        """测试执行报告生成。"""
        intent = Intent(
            type="develop-feature",
            parameters={"requirement_text": "实现登录功能"},
            confidence=0.95,
            raw_message="实现登录功能",
        )

        context = task_orchestrator.orchestrate(intent)

        # 获取执行摘要
        summary = context.get_execution_summary()
        assert summary["status"] == "completed"
        assert summary["total_steps"] == 3
        assert summary["successful_steps"] == 3
        assert summary["failed_steps"] == 0

        # 获取详细报告
        detailed_report = context.get_detailed_report()
        assert "summary" in detailed_report
        assert "steps" in detailed_report
        assert "shared_data" in detailed_report

        # 格式化报告
        formatted_report = context.format_report()
        assert "任务执行报告" in formatted_report
        assert "执行摘要" in formatted_report
        assert "步骤详情" in formatted_report

    def test_system_switching_logging(self, task_orchestrator, caplog):
        """测试系统切换日志记录。"""
        import logging

        intent = Intent(
            type="requirement-to-development",
            parameters={
                "url": "https://github.com/user/repo/issues/1",
                "requirement_text": "实现登录功能",
            },
            confidence=0.90,
            raw_message="查看需求并实现",
        )

        with caplog.at_level(logging.INFO):
            context = task_orchestrator.orchestrate(intent)

        # 验证系统切换日志
        switch_logs = [r for r in caplog.records if "系统切换" in r.message]
        assert len(switch_logs) > 0

    def test_conditional_execution(self, template_loader, task_executor):
        """测试条件执行。"""
        # 创建包含条件步骤的模板
        template = TaskFlowTemplate(
            name="conditional-test",
            description="条件执行测试",
            intent_types=["conditional-test"],
            steps=[
                TemplateStep(system="ide", action="step1", parameters={}),
                TemplateStep(system="ide", action="step2", parameters={}, condition="if_success"),
                TemplateStep(system="ide", action="step3", parameters={}, condition="if_failure"),
            ],
        )
        template_loader.register_template(template)

        orchestrator = TaskOrchestrator(task_executor, template_loader)

        intent = Intent(type="conditional-test", parameters={}, confidence=1.0, raw_message="test")
        context = orchestrator.orchestrate(intent)

        # 第一步和第二步（if_success）应该执行
        assert len(context.step_results) >= 2

    def test_continue_on_error(self, template_loader, task_executor):
        """测试错误后继续执行。"""
        # 创建包含 continue_on_error 的模板
        template = TaskFlowTemplate(
            name="error-test",
            description="错误处理测试",
            intent_types=["error-test"],
            steps=[
                TemplateStep(system="ide", action="step1", parameters={}),
                TemplateStep(system="ide", action="step2", parameters={}, continue_on_error=True),
                TemplateStep(system="ide", action="step3", parameters={}),
            ],
        )
        template_loader.register_template(template)

        orchestrator = TaskOrchestrator(task_executor, template_loader)

        intent = Intent(type="error-test", parameters={}, confidence=1.0, raw_message="test")
        context = orchestrator.orchestrate(intent)

        # 所有步骤都应该执行
        assert len(context.step_results) == 3

    def test_full_workflow_integration(self, task_orchestrator):
        """测试完整的工作流集成。"""
        # 测试从意图识别到任务执行的完整流程
        intent = Intent(
            type="develop-feature",
            parameters={"requirement_text": "实现购物车功能"},
            confidence=0.92,
            raw_message="帮我实现购物车功能",
        )

        # 执行编排
        context = task_orchestrator.orchestrate(intent)

        # 验证结果
        assert context.status == "completed"

        # 验证每个步骤
        for i, step_result in enumerate(context.step_results):
            assert step_result.step_index == i
            assert step_result.success is True
            assert step_result.duration >= 0

    def test_execution_plan_display(self, task_orchestrator):
        """测试执行计划显示。"""
        intent = Intent(
            type="develop-feature",
            parameters={"requirement_text": "实现登录功能"},
            confidence=0.95,
            raw_message="实现登录功能",
        )

        plan = task_orchestrator.show_execution_plan(intent)

        assert plan["intent"] == "develop-feature"
        assert plan["template"] == "develop-feature"
        assert len(plan["steps"]) == 3

    def test_parameter_binding_in_workflow(self, task_orchestrator, task_executor):
        """测试工作流中的参数绑定。"""
        intent = Intent(
            type="develop-feature",
            parameters={"requirement_text": "实现用户注册功能"},
            confidence=0.95,
            raw_message="实现用户注册功能",
        )

        context = task_orchestrator.orchestrate(intent)

        assert context.status == "completed"

        # 验证参数被正确传递到执行器
        ide_actions = [a for a in task_executor._adapters["ide"].executed_actions]
        assert len(ide_actions) > 0

    def test_multiple_sequential_workflows(self, task_orchestrator):
        """测试多个顺序执行的工作流。"""
        intents = [
            Intent(
                type="develop-feature",
                parameters={"requirement_text": f"功能{i}"},
                confidence=0.9,
                raw_message=f"实现功能{i}",
            )
            for i in range(3)
        ]

        for intent in intents:
            context = task_orchestrator.orchestrate(intent)
            assert context.status == "completed"
