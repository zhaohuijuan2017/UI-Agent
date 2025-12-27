"""工作流解析器单元测试。"""

import pytest

from src.workflow.exceptions import WorkflowParseError
from src.workflow.parser import WorkflowParser


@pytest.mark.unit
class TestWorkflowParser:
    """工作流解析器测试。"""

    def test_parse_simple_workflow(self):
        """测试解析简单工作流。"""
        content = """---
name: "测试工作流"
---

# 工作流

## 步骤

1. 激活 PyCharm 窗口
2. 打开文件 main.py
"""
        parser = WorkflowParser()
        config = parser.parse_content(content)

        assert config.name == "测试工作流"
        assert len(config.steps) == 2
        assert config.steps[0].description == "激活 PyCharm 窗口"
        assert config.steps[1].description == "打开文件 main.py"

    def test_parse_workflow_with_yaml_block(self):
        """测试解析带 YAML 配置的工作流。"""
        content = """---
name: "测试工作流"
---

## 步骤

1. 打开文件 main.py

   ```yaml
   operation: double_click_file
   parameters:
     filename: "main.py"
   retry_count: 3
   ```
"""
        parser = WorkflowParser()
        config = parser.parse_content(content)

        assert len(config.steps) == 1
        step = config.steps[0]
        assert step.description == "打开文件 main.py"
        assert step.operation == "double_click_file"
        assert step.parameters["filename"] == "main.py"
        assert step.retry_count == 3

    def test_parse_workflow_with_conditions(self):
        """测试解析带条件的工作流。"""
        content = """# 工作流

## 步骤

1. 激活窗口
2. [if_success] 打开文件
3. [if_failure] 显示错误
"""
        parser = WorkflowParser()
        config = parser.parse_content(content)

        assert len(config.steps) == 3
        assert config.steps[0].condition is None
        assert config.steps[1].condition == "if_success"
        assert config.steps[2].condition == "if_failure"

    def test_parse_file_not_found(self):
        """测试解析不存在的文件。"""
        parser = WorkflowParser()
        with pytest.raises(WorkflowParseError):
            parser.parse_file("not_exist.md")

    def test_parse_empty_workflow(self):
        """测试解析空工作流。"""
        content = """---
name: "空工作流"
---

# 标题
"""
        parser = WorkflowParser()
        config = parser.parse_content(content)

        assert config.name == "空工作流"
        assert len(config.steps) == 0
