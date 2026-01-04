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
        base_url: str | None = None,
    ) -> None:
        """初始化命令解析器。

        Args:
            config_manager: 配置管理器
            api_key: 智谱 AI API Key
            model: 使用的模型名称
            base_url: LLM API Base URL（可选，用于自定义代理）
        """
        self.config = config_manager
        if api_key:
            client_kwargs = {"api_key": api_key}
            if base_url:
                client_kwargs["base_url"] = base_url
            self.client = ZhipuAI(**client_kwargs)
        else:
            self.client = None
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

        # 优先检查浏览器自动化命令
        # 如果命令包含"网页"、"浏览器"、"页面"等关键词，优先匹配浏览器自动化
        browser_keywords = ["网页", "浏览器", "页面", "browser"]
        if any(kw in text_lower for kw in browser_keywords):
            # 查找浏览器自动化相关的操作
            for op_name in self.config.list_operations():
                op = self.config.get_operation(op_name)
                if op and op.intent == "browser_automation":
                    # 检查别名是否匹配
                    for alias in op.aliases:
                        if alias.lower() in text_lower:
                            return op

        # 收集所有匹配的操作及其匹配的别名长度
        matches: list[tuple[OperationConfig, int]] = []

        # 遍历所有操作
        for op_name in self.config.list_operations():
            op = self.config.get_operation(op_name)
            if not op:
                continue

            # 检查操作名称（使用词边界匹配）
            # 使用正则表达式的 \b 确保完整单词匹配
            if re.search(rf'\b{re.escape(op.name.lower())}\b', text_lower):
                matches.append((op, len(op.name)))

            # 检查别名（使用词边界匹配）
            for alias in op.aliases:
                if re.search(rf'\b{re.escape(alias.lower())}\b', text_lower):
                    matches.append((op, len(alias)))

        # 返回别名长度最长的匹配（更具体的匹配优先）
        if matches:
            # 按别名长度降序排序，取第一个
            matches.sort(key=lambda x: x[1], reverse=True)
            return matches[0][0]

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

        # 特殊处理：浏览器自动化命令
        if operation.intent == "browser_automation":
            # 对于浏览器自动化命令，提取操作名称后的所有内容作为定位器
            for alias in operation.aliases + [operation.name]:
                if alias.lower() in text.lower():
                    # 获取操作名称后的内容
                    pattern = rf'{re.escape(alias)}\s+(.+)'
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        # 提取完整的元素描述
                        target = match.group(1).strip()
                        # 去除常见的介词
                        target = re.sub(r'^(中的|名为|叫|target|target:)\s*', '', target)
                        if target:
                            parameters["filename"] = target
                            parameters["locator"] = target
                            break
            return parameters

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

        # 提取输入框相关参数
        if operation.intent == "input" or "input" in operation.name.lower():
            # 提取上下文描述和位置提示
            # 格式: "在{context_text}{position_hint}的输入框中输入{input_text}并回车"
            # 例如: "在本地下方的输入框中输入test并回车"
            context_pattern = r'在\s*([^\s]+?(?:\s*[上下左右]方)?)\s*的输入框中?输入'
            context_match = re.search(context_pattern, text)
            if context_match:
                context_text = context_match.group(1)
                # 检查是否包含位置提示
                position_hints = ["上方", "下方", "左侧", "右边", "右侧"]
                for hint in position_hints:
                    if hint in context_text:
                        parameters["position_hint"] = hint
                        # 移除位置提示，保留上下文文本
                        parameters["context_text"] = context_text.replace(hint, "").strip()
                        break
                else:
                    # 没有位置提示，整个就是上下文
                    parameters["context_text"] = context_text

            # 提取要输入的文本
            # 优先匹配引号包裹的内容
            quoted_pattern = r'输入\s*["\']([^"\']+)["\']'
            quoted_match = re.search(quoted_pattern, text)
            if quoted_match:
                parameters["input_text"] = quoted_match.group(1)
            else:
                # 匹配: "输入xxx并回车" 或 "输入xxx" (支持包含空格的命令)
                # 策略：找到最后一个"输入"关键字后的内容，直到"并回车"或结尾
                # 排除上下文描述部分（包含"输入框"的内容）
                input_text = None
                # 找到所有"输入"的位置
                for match in re.finditer(r'输入', text):
                    pos = match.end()
                    # 检查是否在"输入框中"的上下文内（跳过这种）
                    if pos < len(text) and text[pos:pos+2] == "框":
                        continue
                    # 提取从"输入"后到结束或"并回车"的内容
                    remaining = text[pos:]
                    # 移除"并回车"后的内容
                    if "并回车" in remaining:
                        remaining = remaining.split("并回车")[0]
                    # 清理并提取
                    extracted = remaining.strip()
                    # 排除可能的介词
                    extracted = re.sub(r'^[\s的且和并]+', '', extracted)
                    if extracted:
                        input_text = extracted

                if input_text:
                    # 清理可能的残留字符
                    input_text = re.sub(r'["\']', '', input_text).strip()
                    if input_text:
                        parameters["input_text"] = input_text

            # 检查是否需要回车
            if "回车" in text or "并回车" in text:
                parameters["submit_action"] = "enter"

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
