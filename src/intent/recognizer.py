"""基于 LLM 的意图识别器。"""

import json
import logging
from pathlib import Path

import yaml
from zhipuai import ZhipuAI

from src.intent.models import Intent, IntentDefinition, IntentMatchResult, IntentParameter

logger = logging.getLogger(__name__)


class IntentRecognizer:
    """基于 LLM 的意图识别器。

    通过大模型分析用户消息，识别意图类型并提取参数。
    """

    def __init__(
        self,
        intent_definitions_path: str | None = None,
        llm_client: ZhipuAI | None = None,
        llm_model: str = "glm-4-flash",
        confidence_threshold: float = 0.85,
        base_url: str | None = None,
    ):
        """初始化意图识别器。

        Args:
            intent_definitions_path: 意图定义文件路径（YAML）
            llm_client: LLM 客户端（可选，默认创建新的 ZhipuAI 客户端）
            llm_model: 使用的 LLM 模型名称
            confidence_threshold: 置信度阈值
            base_url: LLM API Base URL（可选，用于自定义代理）
        """
        # 如果提供了 base_url 且没有提供客户端，则创建带 base_url 的客户端
        if base_url and llm_client is None:
            # 需要从外部传入 api_key，这里保持向后兼容
            # 实际使用时应该通过 llm_client 参数传入已配置的客户端
            logger.warning(f"base_url 已设置但未传入 llm_client，请使用已配置 base_url 的客户端")

        self.llm_client = llm_client
        self.llm_model = llm_model
        self.confidence_threshold = confidence_threshold

        # 意图定义存储
        self._intent_definitions: dict[str, IntentDefinition] = {}
        self._definitions_path = intent_definitions_path

        # 加载意图定义
        if intent_definitions_path:
            self.load_definitions(intent_definitions_path)

    def load_definitions(self, path: str) -> None:
        """从 YAML 文件加载意图定义。

        Args:
            path: 意图定义文件路径
        """
        definitions_file = Path(path)
        if not definitions_file.exists():
            logger.warning(f"意图定义文件不存在: {path}")
            return

        with open(definitions_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        intents_data = data.get("intents", {})
        for intent_name, intent_data in intents_data.items():
            # 解析参数定义
            parameters: dict[str, IntentParameter] = {}
            for param_name, param_data in intent_data.get("parameters", {}).items():
                parameters[param_name] = IntentParameter(
                    name=param_name,
                    type=param_data.get("type", "string"),
                    description=param_data.get("description", ""),
                    required=param_data.get("required", True),
                    examples=param_data.get("examples", []),
                    pattern=param_data.get("pattern"),
                )

            # 创建意图定义
            self._intent_definitions[intent_name] = IntentDefinition(
                name=intent_name,
                type=intent_data.get("type", "single-system"),
                description=intent_data.get("description", ""),
                system=intent_data.get("system"),
                systems=intent_data.get("systems", []),
                parameters=parameters,
            )

        logger.info(f"已加载 {len(self._intent_definitions)} 个意图定义")

    def reload_definitions(self) -> bool:
        """重新加载意图定义。

        Returns:
            是否成功重新加载
        """
        if self._definitions_path:
            try:
                self.load_definitions(self._definitions_path)
                return True
            except Exception as e:
                logger.error(f"重新加载意图定义失败: {e}")
                return False
        return False

    def recognize(self, message: str) -> IntentMatchResult:
        """识别用户消息的意图。

        Args:
            message: 用户消息

        Returns:
            意图匹配结果
        """
        if not self.llm_client:
            logger.error("LLM 客户端未配置")
            return IntentMatchResult(intent=None, confidence=0.0)

        if not self._intent_definitions:
            logger.warning("没有可用的意图定义")
            return IntentMatchResult(intent=None, confidence=0.0)

        try:
            # 构建提示词
            prompt = self._build_intent_prompt(message)

            # 调用 LLM
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个意图识别助手，负责分析用户消息并匹配到预定义的意图类型。"
                        "请严格按照 JSON 格式返回结果。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,  # 降低温度以获得更确定的结果
            )

            # 解析响应
            response_text = response.choices[0].message.content.strip()
            logger.debug(f"LLM 响应: {response_text}")

            # 提取 JSON（处理可能的 markdown 代码块）
            json_text = self._extract_json(response_text)
            result_data = json.loads(json_text)

            # 创建意图对象
            intent = Intent(
                type=result_data.get("intent_type", "unknown"),
                parameters=result_data.get("parameters", {}),
                confidence=result_data.get("confidence", 0.0),
                raw_message=message,
                reasoning=result_data.get("reasoning", ""),
            )

            # 检查意图是否有效
            if intent.type == "unknown" or intent.type not in self._intent_definitions:
                logger.warning(f"未知的意图类型: {intent.type}")
                return IntentMatchResult(intent=None, confidence=0.0)

            return IntentMatchResult(intent=intent, confidence=intent.confidence)

        except json.JSONDecodeError as e:
            logger.error(f"解析 LLM 响应失败: {e}")
            return IntentMatchResult(intent=None, confidence=0.0)
        except Exception as e:
            logger.error(f"意图识别失败: {e}")
            return IntentMatchResult(intent=None, confidence=0.0)

    def _build_intent_prompt(self, message: str) -> str:
        """构建意图识别提示词。

        Args:
            message: 用户消息

        Returns:
            提示词字符串
        """
        prompt_parts = [
            "请分析以下用户消息，匹配到最合适的意图类型并提取参数。\n",
            f'用户消息："{message}"\n',
            "可用的意图类型：\n",
        ]

        for intent_idx, (intent_name, intent_def) in enumerate(self._intent_definitions.items()):
            prompt_parts.append(f"{intent_idx + 1}. {intent_name} - {intent_def.description}\n")

            # 添加参数说明
            if intent_def.parameters:
                prompt_parts.append("   参数：\n")
                for param_name, param in intent_def.parameters.items():
                    required_str = "必需" if param.required else "可选"
                    prompt_parts.append(
                        f"   - {param_name}（{param.type}, {required_str}）: {param.description}\n"
                    )
                    if param.examples:
                        prompt_parts.append(f"     示例: {', '.join(param.examples)}\n")

        prompt_parts.extend(
            [
                "\n请以 JSON 格式返回（不要包含其他文字）：\n",
                "```json\n",
                "{\n",
                '  "intent_type": "意图类型",\n',
                '  "confidence": 0.95,\n',
                '  "parameters": {\n',
                '    "参数名": "参数值"\n',
                "  },\n",
                '  "reasoning": "识别理由"\n',
                "}\n",
                "```\n",
            ]
        )

        return "".join(prompt_parts)

    def _extract_json(self, text: str) -> str:
        """从文本中提取 JSON 内容。

        Args:
            text: 可能包含 JSON 的文本

        Returns:
            提取的 JSON 字符串
        """
        # 尝试直接解析
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

        # 尝试提取 markdown 代码块中的 JSON
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end > start:
                return text[start:end].strip()

        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end > start:
                json_block = text[start:end].strip()
                if json_block.startswith("json"):
                    return json_block[4:].strip()
                return json_block

        return text

    def get_available_intents(self) -> list[str]:
        """获取所有可用的意图类型。

        Returns:
            意图类型列表
        """
        return list(self._intent_definitions.keys())

    def get_intent_definition(self, intent_type: str) -> IntentDefinition | None:
        """获取意图定义。

        Args:
            intent_type: 意图类型

        Returns:
            意图定义，如果不存在则返回 None
        """
        return self._intent_definitions.get(intent_type)
