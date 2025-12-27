"""工作流执行集成测试。"""

import os
import tempfile
from pathlib import Path

import pytest

from src.controller.ide_controller import IDEController
from src.workflow.exceptions import WorkflowError


@pytest.fixture
def ide_controller():
    """创建 IDE 控制器测试实例。"""
    # 获取项目根目录
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "main.yaml")
    # 使用测试 API key（或从环境变量获取）
    api_key = os.environ.get("ZHIPUAI_API_KEY", "test-key-for-testing")

    controller = IDEController(config_path=config_path, api_key=api_key)
    yield controller
    # 清理
    if controller._workflow_executor:
        controller._workflow_executor = None


@pytest.fixture
def temp_workflow_file():
    """创建临时工作流文件。"""
    content = """---
name: "测试工作流"
description: "集成测试工作流"
---

# 测试工作流

## 步骤

1. 激活 PyCharm 窗口
2. 双击文件 main.py
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # 清理
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def temp_workflow_with_yaml_config():
    """创建带 YAML 配置的临时工作流文件。"""
    content = """---
name: "带配置的测试工作流"
description: "测试 YAML 配置解析"
---

# 测试工作流

## 步骤

1. 激活窗口

2. 双击文件 test.py

   ```yaml
   operation: double_click_file
   parameters:
     filename: "test.py"
   retry_count: 2
   ```

3. [if_success] 打开文件 main.py
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(content)
        temp_path = f.name

    yield temp_path

    # 清理
    Path(temp_path).unlink(missing_ok=True)


class TestWorkflowExecutionIntegration:
    """工作流执行集成测试。"""

    def test_execute_workflow_file_dry_run(self, ide_controller, temp_workflow_file):
        """测试 dry-run 模式执行工作流文件。"""
        result = ide_controller.execute_workflow_file(temp_workflow_file, dry_run=True)

        assert result.status.value == "success"
        assert "workflow_name" in result.data
        assert result.data["workflow_name"] == "测试工作流"

    def test_execute_workflow_with_yaml_config(
        self, ide_controller, temp_workflow_with_yaml_config
    ):
        """测试执行带 YAML 配置的工作流。"""
        result = ide_controller.execute_workflow_file(temp_workflow_with_yaml_config, dry_run=True)

        assert result.status.value == "success"
        assert result.data["workflow_name"] == "带配置的测试工作流"

    def test_validate_workflow_file(self, ide_controller, temp_workflow_file):
        """测试验证工作流文件。"""
        result = ide_controller.validate_workflow_file(temp_workflow_file)

        assert result.status.value == "success"
        assert "workflow_name" in result.data
        assert result.data["valid"] is True

    def test_validate_invalid_workflow_file(self, ide_controller):
        """测试验证无效的工作流文件。"""
        # 创建没有名称的工作流
        content = """# 无效工作流

## 步骤

1. 激活窗口
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            result = ide_controller.validate_workflow_file(temp_path)
            # 应该返回验证错误
            assert result.status.value == "error"
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_execute_nonexistent_workflow_file(self, ide_controller):
        """测试执行不存在的工作流文件。"""
        with pytest.raises(WorkflowError):
            ide_controller.execute_workflow_file("nonexistent_workflow.md")

    def test_workflow_parser_integration(self, ide_controller, temp_workflow_file):
        """测试工作流解析器集成。"""
        config = ide_controller._workflow_parser.parse_file(temp_workflow_file)

        assert config.name == "测试工作流"
        assert config.description == "集成测试工作流"
        assert len(config.steps) == 2
        assert config.steps[0].description == "激活 PyCharm 窗口"
        assert config.steps[1].description == "双击文件 main.py"

    def test_workflow_validator_integration(self, ide_controller, temp_workflow_file):
        """测试工作流验证器集成。"""
        config = ide_controller._workflow_parser.parse_file(temp_workflow_file)
        errors = ide_controller._workflow_validator.validate(config)

        assert len(errors) == 0

    def test_workflow_with_conditions(self, ide_controller):
        """测试带条件的工作流。"""
        content = """---
name: "条件测试工作流"
---

## 步骤

1. 激活窗口
2. [if_success] 双击文件 main.py
3. [if_failure] 显示错误信息
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = ide_controller._workflow_parser.parse_content(content)

            assert len(config.steps) == 3
            assert config.steps[0].condition is None
            assert config.steps[1].condition == "if_success"
            assert config.steps[2].condition == "if_failure"
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_workflow_with_retry_config(self, ide_controller):
        """测试带重试配置的工作流。"""
        content = """---
name: "重试测试工作流"
---

## 步骤

1. 激活窗口

2. 双击文件 test.py

   ```yaml
   retry_count: 3
   retry_interval: 2.0
   ```

3. 打开文件 main.py
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write(content)
            temp_path = f.name

        try:
            config = ide_controller._workflow_parser.parse_content(content)

            assert len(config.steps) == 3
            assert config.steps[1].retry_count == 3
            assert config.steps[1].retry_interval == 2.0
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_workflow_executor_initialization(self, ide_controller, temp_workflow_file):
        """测试工作流执行器延迟初始化。"""
        # 执行前执行器应为 None
        assert ide_controller._workflow_executor is None

        # 执行工作流（dry-run）
        ide_controller.execute_workflow_file(temp_workflow_file, dry_run=True)

        # 执行后执行器应该被初始化
        assert ide_controller._workflow_executor is not None

    def test_workflow_result_structure(self, ide_controller, temp_workflow_file):
        """测试工作流执行结果结构。"""
        result = ide_controller.execute_workflow_file(temp_workflow_file, dry_run=True)

        assert result.status.value == "success"
        assert "workflow_name" in result.data
        assert "completed_steps" in result.data
        assert "total_steps" in result.data
        assert "success" in result.data
        assert result.data["workflow_name"] == "测试工作流"
        assert result.data["total_steps"] == 2
