"""自然语言命令解析器。"""

import re
from typing import Any

from zhipuai import ZhipuAI

from src.config.config_manager import ConfigManager
from src.config.schema import OperationConfig
from src.models.command import ParsedCommand
from src.parser.intents import INTENT_KEYWORDS, IntentType


class CommandParser:
    """自然语言命令解析器。"""

    def __init__(
        self,
        config_manager: ConfigManager,
        api_key: str,
        model: str = "glm-4-flash",
    ) -> None:
        """初始化命令解析器。

        Args:
            config_manager: 配置管理器
            api_key: 智谱 AI API Key
            model: 使用的模型名称
        """
        self.config = config_manager
        self.client = ZhipuAI(api_key=api_key) if api_key else None
        self.model = model

    def parse(self, text: str, context: dict[str, Any] | None = None) -> ParsedCommand:
        """解析自然语言命令。

        Args:
            text: 自然语言命令文本
            context: 上下文信息

        Returns:
            解析后的命令对象
        """
        context = context or {}

        # 首先尝试从配置中匹配操作
        matched_op = self._match_operation(text)
        if matched_op:
            # 提取参数
            parameters = self._extract_parameters(text, matched_op)

            return ParsedCommand(
                intent=matched_op.intent,
                action=matched_op.name,
                parameters=parameters,
                confidence=0.95,
                context=context,
            )

        # 如果没有匹配到配置的操作，使用 NLP 解析
        if self.client:
            return self._parse_with_llm(text, context)

        # 回退到规则匹配
        return self._parse_with_rules(text, context)

    def _match_operation(self, text: str) -> OperationConfig | None:
        """从配置中匹配操作。

        Args:
            text: 命令文本

        Returns:
            匹配到的操作配置，如果未匹配则返回 None
        """
        text_lower = text.lower().strip()

        # 遍历所有操作
        for op_name in self.config.list_operations():
            op = self.config.get_operation(op_name)
            if not op:
                continue

            # 检查操作名称和别名
            if op.name.lower() in text_lower:
                return op

            for alias in op.aliases:
                if alias.lower() in text_lower:
                    return op

        return None

    def _extract_parameters(self, text: str, operation: OperationConfig) -> dict[str, Any]:
        """从命令文本中提取参数。

        Args:
            text: 命令文本
            operation: 操作配置

        Returns:
            提取的参数字典
        """
        parameters: dict[str, Any] = {}

        # 提取文件名/目标关键字（优先级从高到低）
        # 1. 引号包裹的内容（最精确）
        file_match = re.search(r'["\']([^"\']+)["\']', text)
        if file_match:
            parameters["filename"] = file_match.group(1)
        else:
            # 2. 带扩展名的文件
            file_match = re.search(r'([\w\-./]+\.(?:py|js|ts|java|cpp|txt|md|json|yaml|yml|html|css|xml))', text)
            if file_match:
                parameters["filename"] = file_match.group(1)
            else:
                # 3. 通用关键字：提取操作名称后的文本作为目标
                # 例如 "双击 main" -> "main", "点击 运行按钮" -> "运行按钮"
                for alias in operation.aliases + [operation.name]:
                    if alias.lower() in text.lower():
                        # 获取操作名称后的内容
                        pattern = rf'{re.escape(alias)}\s+(.+)'
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            # 清理提取的目标（去除可能的介词）
                            target = match.group(1).strip()
                            target = re.sub(r'^(中的|名为|叫|target|target:)\s*', '', target)
                            if target:
                                parameters["filename"] = target
                                break

        # 提取行号
        line_match = re.search(r'(\d+)\s*行|line\s*(\d+)|第\s*(\d+)\s*行', text)
        if line_match:
            parameters["line_number"] = int(line_match.group(1) or line_match.group(2) or line_match.group(3))

        # 提取符号名
        symbol_match = re.search(r'为\s*["\']?([\w_]+)["\']?|名为\s*["\']?([\w_]+)["\']?', text)
        if symbol_match:
            parameters["new_name"] = symbol_match.group(1) or symbol_match.group(2)

        # 提取搜索文本
        search_match = re.search(r'["\']([^"\']+)["\']|\s+(.+)$', text)
        if search_match and "search" in operation.name.lower():
            parameters["search_text"] = search_match.group(1) or search_match.group(2)

        return parameters

    def _parse_with_llm(self, text: str, context: dict[str, Any]) -> ParsedCommand:
        """使用 LLM 解析命令。

        Args:
            text: 命令文本
            context: 上下文信息

        Returns:
            解析后的命令对象
        """
        # 构建提示词
        available_ops = [self.config.get_operation(name) for name in self.config.list_operations()]
        op_list = "\n".join(
            f"- {op.name}: {op.description} (别名: {', '.join(op.aliases)})" for op in available_ops if op
        )

        prompt = f"""你是一个 IDE 命令解析器。请解析用户的自然语言命令，返回结构化的结果。

可用的操作列表：
{op_list}

请解析以下命令，并返回 JSON 格式的结果：
{{
    "intent": "意图类型",
    "action": "操作名称",
    "parameters": {{"参数名": "参数值"}},
    "confidence": 0.95
}}

用户命令：{text}

只返回 JSON，不要其他内容。"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )

            result_text = response.choices[0].message.content.strip()
            # 移除可能的 markdown 代码块标记
            result_text = result_text.removeprefix("```json").removeprefix("```").strip()

            import json

            result = json.loads(result_text)

            return ParsedCommand(
                intent=result.get("intent", IntentType.UNKNOWN.value),
                action=result.get("action", ""),
                parameters=result.get("parameters", {}),
                confidence=result.get("confidence", 0.8),
                context=context,
            )
        except Exception:
            # LLM 调用失败，回退到规则匹配
            return self._parse_with_rules(text, context)

    def _parse_with_rules(self, text: str, context: dict[str, Any]) -> ParsedCommand:
        """使用规则匹配解析命令。

        Args:
            text: 命令文本
            context: 上下文信息

        Returns:
            解析后的命令对象
        """
        text_lower = text.lower()

        # 意图分类
        intent = IntentType.UNKNOWN
        for intent_type, keywords in INTENT_KEYWORDS.items():
            if any(keyword in text_lower for keyword in keywords):
                intent = intent_type
                break

        # 提取操作
        action = "unknown"
        matched_op = None
        for op_name in self.config.list_operations():
            op = self.config.get_operation(op_name)
            if op and op.intent == intent.value:
                if any(alias in text_lower for alias in op.aliases):
                    action = op.name
                    matched_op = op
                    break

        # 提取参数（使用与 _extract_parameters 相同的逻辑）
        parameters: dict[str, Any] = {}
        if matched_op:
            parameters = self._extract_parameters(text, matched_op)

        return ParsedCommand(
            intent=intent.value,
            action=action,
            parameters=parameters,
            confidence=0.6,
            context=context,
        )

    def validate(self, command: ParsedCommand) -> bool:
        """验证命令有效性。

        Args:
            command: 解析后的命令

        Returns:
            是否有效
        """
        return command.validate()
