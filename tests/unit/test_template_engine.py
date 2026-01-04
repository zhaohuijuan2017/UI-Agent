"""模板引擎单元测试。"""

import pytest

from src.intent.models import Intent
from src.templates.engine import TemplateEngine
from src.templates.models import TaskFlowTemplate, TemplateStep


@pytest.fixture
def template_engine():
    """创建模板引擎实例。"""
    return TemplateEngine()


@pytest.fixture
def sample_intent():
    """创建示例意图。"""
    return Intent(
        type="develop-feature",
        parameters={
            "requirement_text": "实现用户登录功能",
            "url": "https://example.com/issue/1",
        },
        confidence=0.95,
        raw_message="帮我实现登录功能",
        reasoning="匹配到开发意图",
    )


@pytest.fixture
def sample_template():
    """创建示例模板。"""
    return TaskFlowTemplate(
        name="develop-feature",
        description="需求开发模板",
        intent_types=["develop-feature"],
        steps=[
            TemplateStep(
                system="ide",
                action="switch_ide",
                parameters={"ide_name": "PyCharm"},
            ),
            TemplateStep(
                system="ide",
                action="generate_code",
                parameters={"requirement": "{{intent.requirement_text}}"},
            ),
            TemplateStep(
                system="ide",
                action="activate_plugin",
                parameters={"plugin_name": "ai-assistant"},
                condition="if_success",
            ),
        ],
    )


class TestTemplateEngine:
    """模板引擎测试类。"""

    def test_bind_parameters_basic(self, template_engine, sample_template, sample_intent):
        """测试基本参数绑定。"""
        context_data = {}

        bound_template = template_engine.bind_parameters(
            sample_template, sample_intent, context_data
        )

        assert bound_template.name == sample_template.name
        assert bound_template.description == sample_template.description
        assert len(bound_template.steps) == len(sample_template.steps)

        # 检查第二个步骤的参数绑定
        second_step = bound_template.steps[1]
        assert second_step.parameters["requirement"] == "实现用户登录功能"

    def test_bind_parameters_with_context_data(self, template_engine, sample_template, sample_intent):
        """测试使用上下文数据进行参数绑定。"""
        context_data = {
            "custom_param": "custom_value",
            "ide_name": "VSCode",
        }

        bound_template = template_engine.bind_parameters(
            sample_template, sample_intent, context_data
        )

        # 上下文数据和意图参数都会被使用
        first_step = bound_template.steps[0]
        assert first_step.parameters["ide_name"] == "PyCharm"  # 来自模板原始参数

    def test_bind_parameters_with_input_from(self, template_engine):
        """测试 input_from 功能。"""
        template = TaskFlowTemplate(
            name="test-template",
            description="测试模板",
            intent_types=["test"],
            steps=[
                TemplateStep(
                    system="browser",
                    action="extract_data",
                    parameters={},
                    output_to="extracted_data",
                ),
                TemplateStep(
                    system="ide",
                    action="use_data",
                    parameters={},
                    input_from="extracted_data",
                ),
            ],
        )

        intent = Intent(type="test", parameters={}, confidence=1.0, raw_message="test")
        # 使用非字典类型测试 input_data 保存
        context_data = {"extracted_data": "string_data_value"}

        bound_template = template_engine.bind_parameters(template, intent, context_data)

        # 第二个步骤应该从上下文读取数据
        second_step = bound_template.steps[1]
        assert "input_data" in second_step.parameters
        assert second_step.parameters["input_data"] == "string_data_value"

    def test_replace_placeholders_string(self, template_engine):
        """测试字符串占位符替换。"""
        params = {"requirement_text": "实现登录功能"}

        result = template_engine._replace_placeholders(
            "{{intent.requirement_text}}", params
        )

        assert result == "实现登录功能"

    def test_replace_placeholders_number(self, template_engine):
        """测试数字替换。"""
        params = {"count": "42"}

        result = template_engine._replace_placeholders("{{intent.count}}", params)

        assert result == 42

    def test_replace_placeholders_float(self, template_engine):
        """测试浮点数替换。"""
        params = {"price": "99.99"}

        result = template_engine._replace_placeholders("{{intent.price}}", params)

        assert result == 99.99

    def test_replace_placeholders_boolean(self, template_engine):
        """测试布尔值替换。"""
        params = {"enabled": "true"}

        result = template_engine._replace_placeholders("{{intent.enabled}}", params)

        assert result is True

    def test_replace_placeholders_not_found(self, template_engine):
        """测试占位符不存在时保持原样。"""
        params = {"other": "value"}

        result = template_engine._replace_placeholders("{{intent.missing}}", params)

        assert result == "{{intent.missing}}"

    def test_should_execute_step_no_condition(self, template_engine):
        """测试无条件时总是执行。"""
        step = TemplateStep(system="test", action="test", condition=None)

        assert template_engine.should_execute_step(step, None) is True
        assert template_engine.should_execute_step(step, True) is True
        assert template_engine.should_execute_step(step, False) is True

    def test_should_execute_step_if_success(self, template_engine):
        """测试 if_success 条件。"""
        step = TemplateStep(system="test", action="test", condition="if_success")

        # 第一步总是执行
        assert template_engine.should_execute_step(step, None) is True
        # 上一步成功时执行
        assert template_engine.should_execute_step(step, True) is True
        # 上一步失败时不执行
        assert template_engine.should_execute_step(step, False) is False

    def test_should_execute_step_if_failure(self, template_engine):
        """测试 if_failure 条件。"""
        step = TemplateStep(system="test", action="test", condition="if_failure")

        # 第一步总是执行
        assert template_engine.should_execute_step(step, None) is True
        # 上一步成功时不执行
        assert template_engine.should_execute_step(step, True) is False
        # 上一步失败时执行
        assert template_engine.should_execute_step(step, False) is True

    def test_extract_output_data(self, template_engine):
        """测试提取输出数据。"""
        step = TemplateStep(
            system="test", action="test", output_to="output_key"
        )
        step_result = {"data": "value"}

        output = template_engine.extract_output_data(step_result, step)

        assert output == {"output_key": step_result}

    def test_extract_output_data_no_output_to(self, template_engine):
        """测试没有 output_to 时返回空字典。"""
        step = TemplateStep(system="test", action="test", output_to=None)
        step_result = {"data": "value"}

        output = template_engine.extract_output_data(step_result, step)

        assert output == {}

    def test_bind_parameters_preserves_template_structure(self, template_engine, sample_template, sample_intent):
        """测试参数绑定保持模板结构。"""
        bound_template = template_engine.bind_parameters(
            sample_template, sample_intent, {}
        )

        # 检查所有属性都被保留
        assert bound_template.name == sample_template.name
        assert bound_template.description == sample_template.description
        assert bound_template.intent_types == sample_template.intent_types
        assert len(bound_template.steps) == len(sample_template.steps)

        # 检查每个步骤的条件和其他属性
        for i, step in enumerate(bound_template.steps):
            assert step.system == sample_template.steps[i].system
            assert step.action == sample_template.steps[i].action
            assert step.condition == sample_template.steps[i].condition
            assert step.continue_on_error == sample_template.steps[i].continue_on_error

    def test_bind_parameters_multiple_placeholders(self, template_engine):
        """测试一个参数中有多个占位符。"""
        template = TaskFlowTemplate(
            name="test",
            description="测试",
            intent_types=["test"],
            steps=[
                TemplateStep(
                    system="test",
                    action="test",
                    parameters={
                        "message": "需求: {{intent.requirement}}, URL: {{intent.url}}"
                    },
                ),
            ],
        )

        intent = Intent(
            type="test",
            parameters={"requirement": "登录功能", "url": "https://example.com"},
            confidence=1.0,
            raw_message="test",
        )

        bound_template = template_engine.bind_parameters(template, intent, {})

        assert bound_template.steps[0].parameters["message"] == "需求: 登录功能, URL: https://example.com"

    def test_bind_parameters_no_placeholders(self, template_engine):
        """测试没有占位符时保持原值。"""
        template = TaskFlowTemplate(
            name="test",
            description="测试",
            intent_types=["test"],
            steps=[
                TemplateStep(
                    system="test",
                    action="test",
                    parameters={"constant": "fixed_value"},
                ),
            ],
        )

        intent = Intent(type="test", parameters={}, confidence=1.0, raw_message="test")

        bound_template = template_engine.bind_parameters(template, intent, {})

        assert bound_template.steps[0].parameters["constant"] == "fixed_value"
