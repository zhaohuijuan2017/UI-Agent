"""工作流 Markdown 解析器。"""

import re
from pathlib import Path

import yaml

from src.workflow.exceptions import WorkflowParseError
from src.workflow.models import WorkflowConfig, WorkflowStep


class WorkflowParser:
    """工作流解析器。"""

    def parse_file(self, path: str) -> WorkflowConfig:
        """解析工作流文件。

        Args:
            path: 工作流文件路径

        Returns:
            工作流配置
        """
        try:
            content = Path(path).read_text(encoding="utf-8")
            return self.parse_content(content)
        except FileNotFoundError:
            raise WorkflowParseError(f"工作流文件不存在: {path}")
        except Exception as e:
            raise WorkflowParseError(f"读取文件失败: {e}")

    def parse_content(self, content: str) -> WorkflowConfig:
        """解析工作流内容。

        Args:
            content: Markdown 内容

        Returns:
            工作流配置
        """
        # 提取 YAML front matter
        metadata = self._extract_front_matter(content)

        # 移除 front matter，获取纯内容
        body_content = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                body_content = parts[2].lstrip()

        # 提取步骤
        steps = self._extract_steps(body_content)

        # 构建配置
        name = metadata.get("name", "未命名工作流")
        description = metadata.get("description", "")
        variables = metadata.get("variables", {})

        return WorkflowConfig(
            name=name,
            description=description,
            steps=steps,
            variables=variables,
            metadata=metadata,
        )

    def _extract_front_matter(self, content: str) -> dict:
        """提取 YAML front matter。

        Args:
            content: Markdown 内容

        Returns:
            元数据字典
        """
        if not content.startswith("---"):
            return {}

        # 查找第二个 ---
        parts = content.split("---", 2)
        if len(parts) < 3:
            return {}

        try:
            yaml_content = parts[1].strip()
            return yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError as e:
            raise WorkflowParseError(f"YAML front matter 解析失败: {e}")

    def _extract_steps(self, content: str) -> list[WorkflowStep]:
        """提取步骤列表。

        Args:
            content: Markdown 内容（不含 front matter）

        Returns:
            步骤列表
        """
        steps = []

        # 匹配有序列表（1. 2. 3. 等）
        # 使用正则表达式找到所有列表项
        lines = content.split("\n")

        current_step = None
        current_yaml_block: list[str] = []
        in_yaml_block = False

        for i, line in enumerate(lines, 1):
            # 检查是否是列表项
            list_match = re.match(r"^(\d+)\.\s+(.+)", line)
            if list_match:
                # 保存上一步（如果有）
                if current_step:
                    # 解析 YAML 块（如果有）
                    if current_yaml_block:
                        yaml_content = "\n".join(current_yaml_block)
                        self._apply_yaml_config(current_step, yaml_content, i)
                    steps.append(current_step)

                # 创建新步骤
                step_text = list_match.group(2).strip()
                current_step, condition = self._parse_step_description(step_text, i)

                # 重置 YAML 块
                current_yaml_block = []
                in_yaml_block = False

            elif current_step:
                # 检查是否是代码块开始
                if line.strip().startswith("```"):
                    if in_yaml_block:
                        # YAML 块结束
                        in_yaml_block = False
                    elif "yaml" in line.lower() or "yml" in line.lower():
                        # YAML 块开始
                        in_yaml_block = True
                elif in_yaml_block:
                    current_yaml_block.append(line)

        # 保存最后一步
        if current_step:
            if current_yaml_block:
                yaml_content = "\n".join(current_yaml_block)
                self._apply_yaml_config(current_step, yaml_content, len(lines))
            steps.append(current_step)

        return steps

    def _parse_step_description(
        self, text: str, line_number: int
    ) -> tuple[WorkflowStep, str | None]:
        """解析步骤描述。

        Args:
            text: 步骤文本
            line_number: 行号

        Returns:
            (步骤对象, 条件)
        """
        # 检查条件标记 [if_success] [if_failure] [if ...]
        condition = None
        description = text

        # 匹配条件标记
        condition_match = re.match(r"^\[(if_[a-zA-Z_]+|if\s+.+?)\]\s*(.+)", text)
        if condition_match:
            condition = condition_match.group(1).strip()
            description = condition_match.group(2).strip()

        return WorkflowStep(description=description, condition=condition), condition

    def _apply_yaml_config(self, step: WorkflowStep, yaml_content: str, line_number: int) -> None:
        """应用 YAML 配置到步骤。

        Args:
            step: 步骤对象
            yaml_content: YAML 内容
            line_number: 行号
        """
        try:
            config = yaml.safe_load(yaml_content)
            if not isinstance(config, dict):
                return

            # 应用配置
            if "operation" in config:
                step.operation = config["operation"]
            if "parameters" in config:
                step.parameters.update(config["parameters"])
            if "retry_count" in config:
                step.retry_count = config["retry_count"]
            if "retry_interval" in config:
                step.retry_interval = config["retry_interval"]
            if "continue_on_error" in config:
                step.continue_on_error = config["continue_on_error"]
            if "condition" in config:
                step.condition = config["condition"]

        except yaml.YAMLError as e:
            raise WorkflowParseError(f"YAML 配置解析失败: {e}", line_number=line_number)
