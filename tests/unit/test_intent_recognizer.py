"""意图识别器单元测试。"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest
import yaml

from src.intent.models import Intent, IntentMatchResult
from src.intent.recognizer import IntentRecognizer


@pytest.fixture
def intent_definitions_file():
    """创建测试用的意图定义文件。"""
    definitions = {
        "intents": {
            "develop-feature": {
                "type": "single-system",
                "description": "需求开发",
                "system": "ide",
                "parameters": {
                    "requirement_text": {
                        "type": "string",
                        "description": "需求文本",
                        "required": True,
                        "examples": ["实现登录功能"],
                    }
                },
            },
            "view-requirement": {
                "type": "single-system",
                "description": "需求查看",
                "system": "browser",
                "parameters": {
                    "url": {
                        "type": "string",
                        "description": "需求链接",
                        "required": True,
                        "pattern": "https?://\\S+",
                    }
                },
            },
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        yaml.dump(definitions, f, allow_unicode=True)
        temp_path = f.name

    yield temp_path

    # 清理
    Path(temp_path).unlink()


@pytest.fixture
def mock_llm_client():
    """模拟 LLM 客户端。"""
    client = MagicMock()

    # 模拟成功响应
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '''```json
{
  "intent_type": "develop-feature",
  "confidence": 0.95,
  "parameters": {
    "requirement_text": "实现用户登录功能"
  },
  "reasoning": "用户想要实现登录功能，匹配到开发意图"
}
```'''
    client.chat.completions.create = MagicMock(return_value=mock_response)

    return client


@pytest.fixture
def recognizer(intent_definitions_file, mock_llm_client):
    """创建意图识别器实例。"""
    return IntentRecognizer(
        intent_definitions_path=intent_definitions_file,
        llm_client=mock_llm_client,
        llm_model="glm-4-flash",
        confidence_threshold=0.85,
    )


class TestIntentRecognizer:
    """意图识别器测试类。"""

    def test_init(self, intent_definitions_file, mock_llm_client):
        """测试初始化。"""
        recognizer = IntentRecognizer(
            intent_definitions_path=intent_definitions_file,
            llm_client=mock_llm_client,
        )

        assert recognizer.llm_client is mock_llm_client
        assert recognizer._definitions_path == intent_definitions_file
        assert len(recognizer._intent_definitions) == 2

    def test_load_definitions(self, recognizer):
        """测试加载意图定义。"""
        assert "develop-feature" in recognizer._intent_definitions
        assert "view-requirement" in recognizer._intent_definitions

        intent_def = recognizer._intent_definitions["develop-feature"]
        assert intent_def.name == "develop-feature"
        assert intent_def.type == "single-system"
        assert intent_def.system == "ide"
        assert "requirement_text" in intent_def.parameters

    def test_reload_definitions(self, recognizer, intent_definitions_file):
        """测试重新加载意图定义。"""
        result = recognizer.reload_definitions()
        assert result is True

    def test_recognize_success(self, recognizer):
        """测试成功识别意图。"""
        result = recognizer.recognize("帮我实现用户登录功能")

        assert result.intent is not None
        assert result.intent.type == "develop-feature"
        assert result.confidence == 0.95
        assert result.intent.parameters["requirement_text"] == "实现用户登录功能"

    def test_recognize_with_confidence_below_threshold(self, mock_llm_client, intent_definitions_file):
        """测试置信度低于阈值的情况。"""
        # 修改模拟响应为低置信度
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```json
{
  "intent_type": "develop-feature",
  "confidence": 0.70,
  "parameters": {
    "requirement_text": "实现登录功能"
  },
  "reasoning": "不太确定"
}
```'''
        mock_llm_client.chat.completions.create = MagicMock(return_value=mock_response)

        recognizer = IntentRecognizer(
            intent_definitions_path=intent_definitions_file,
            llm_client=mock_llm_client,
            confidence_threshold=0.85,
        )

        result = recognizer.recognize("帮我实现登录功能")

        # 仍然应该识别成功，但置信度低于阈值
        assert result.intent is not None
        assert result.confidence == 0.70

    def test_recognize_unknown_intent(self, mock_llm_client, intent_definitions_file):
        """测试识别未知意图。"""
        # 模拟返回未知意图
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```json
{
  "intent_type": "unknown",
  "confidence": 0.5,
  "parameters": {},
  "reasoning": "无法识别意图"
}
```'''
        mock_llm_client.chat.completions.create = MagicMock(return_value=mock_response)

        recognizer = IntentRecognizer(
            intent_definitions_path=intent_definitions_file,
            llm_client=mock_llm_client,
        )

        result = recognizer.recognize("今天天气怎么样")

        assert result.intent is None
        assert result.confidence == 0.0

    def test_recognize_no_llm_client(self, intent_definitions_file):
        """测试没有配置 LLM 客户端的情况。"""
        recognizer = IntentRecognizer(
            intent_definitions_path=intent_definitions_file,
            llm_client=None,
        )

        result = recognizer.recognize("帮我实现登录功能")

        assert result.intent is None
        assert result.confidence == 0.0

    def test_recognize_json_decode_error(self, mock_llm_client, intent_definitions_file):
        """测试 JSON 解析失败的情况。"""
        # 模拟返回无效 JSON
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "这不是有效的 JSON"
        mock_llm_client.chat.completions.create = MagicMock(return_value=mock_response)

        recognizer = IntentRecognizer(
            intent_definitions_path=intent_definitions_file,
            llm_client=mock_llm_client,
        )

        result = recognizer.recognize("帮我实现登录功能")

        assert result.intent is None
        assert result.confidence == 0.0

    def test_extract_json_with_markdown(self, recognizer):
        """测试从 markdown 代码块中提取 JSON。"""
        json_text = recognizer._extract_json('''```json
{"key": "value"}
```''')
        assert json_text == '{"key": "value"}'

    def test_extract_json_without_markdown(self, recognizer):
        """测试提取纯 JSON。"""
        json_text = recognizer._extract_json('{"key": "value"}')
        assert json_text == '{"key": "value"}'

    def test_get_available_intents(self, recognizer):
        """测试获取可用意图列表。"""
        intents = recognizer.get_available_intents()
        assert "develop-feature" in intents
        assert "view-requirement" in intents

    def test_get_intent_definition(self, recognizer):
        """测试获取意图定义。"""
        intent_def = recognizer.get_intent_definition("develop-feature")
        assert intent_def is not None
        assert intent_def.name == "develop-feature"

    def test_get_intent_definition_not_found(self, recognizer):
        """测试获取不存在的意图定义。"""
        intent_def = recognizer.get_intent_definition("non-existent")
        assert intent_def is None

    def test_recognize_view_requirement(self, recognizer):
        """测试识别查看需求意图。"""
        # 修改模拟响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```json
{
  "intent_type": "view-requirement",
  "confidence": 0.90,
  "parameters": {
    "url": "https://github.com/user/repo/issues/1"
  },
  "reasoning": "用户想要查看需求链接"
}
```'''

        # 模拟 LLM 客户端
        recognizer.llm_client.chat.completions.create = MagicMock(return_value=mock_response)

        result = recognizer.recognize("帮我查看这个需求 https://github.com/user/repo/issues/1")

        assert result.intent is not None
        assert result.intent.type == "view-requirement"
        assert result.confidence == 0.90
        assert result.intent.parameters["url"] == "https://github.com/user/repo/issues/1"

    def test_build_intent_prompt(self, recognizer):
        """测试构建意图识别提示词。"""
        prompt = recognizer._build_intent_prompt("帮我实现登录功能")

        assert "帮我实现登录功能" in prompt
        assert "develop-feature" in prompt
        assert "view-requirement" in prompt
        assert "requirement_text" in prompt
        assert "url" in prompt
        assert "JSON" in prompt
