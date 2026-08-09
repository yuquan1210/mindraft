import json
import os
import sys
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.llm.base import BaseLLM
from scripts.llm_factory import get_llm
from scripts.utils import load_config

# 0. 验证 extract_json 能容忍字符串值内未转义的控制字符（低思考模式常见缺陷）
raw_control_char_json = '{"title": "Test", "rewritten_content": "line1\nline2"}'
parsed = BaseLLM.extract_json(raw_control_char_json)
assert parsed["rewritten_content"] == "line1\nline2", f"意外解析结果: {parsed}"
print("[extract_json] ✓ 容忍字符串内控制字符")


class FakeOpenAIClient:
    """模拟 OpenAI 客户端，返回可控响应。"""

    def __init__(self, response_text: str):
        self._response_text = response_text

    def chat_completions_create(self, **kwargs):
        msg = Mock()
        msg.content = self._response_text
        choice = Mock()
        choice.message = msg
        response = Mock()
        response.choices = [choice]
        return response

    def __getattr__(self, name):
        if name == "chat":
            return Mock(completions=Mock(create=self.chat_completions_create))
        raise AttributeError(name)


# 1. 验证 load_config 和 get_llm 可正常工作
config = load_config()
print(f"[config] provider={config['llm_provider']}, model={config['llm_model']}")

# 2. 使用 Mock 验证 chat 返回文本（patch 当前 provider 对应的 OpenAI 客户端）
openai_target = f"scripts.llm.{config['llm_provider']}.OpenAI"
with patch(openai_target) as mock_openai:
    mock_client = FakeOpenAIClient("模拟的 LLM 文本响应")
    mock_openai.return_value = mock_client
    llm = get_llm(config)
    response = llm.chat(
        system="你是一个测试助手。",
        user="请回复固定文本。",
    )
    assert response == "模拟的 LLM 文本响应", f"意外响应: {response}"
    print(f"[chat mock] ✓ {response}")

# 3. 使用 Mock 验证 chat_json 能解析 JSON 并兜底处理 markdown 包裹
json_payload = {"greeting": "你好", "language": "中文"}
markdown_wrapped = f"```json\n{json.dumps(json_payload, ensure_ascii=False)}\n```"

with patch(openai_target) as mock_openai:
    mock_client = FakeOpenAIClient(markdown_wrapped)
    mock_openai.return_value = mock_client
    llm = get_llm(config)
    result = llm.chat_json(
        system="你是一个 JSON 生成助手。",
        user="请返回 JSON。",
    )
    assert result == json_payload, f"意外解析结果: {result}"
    print(f"[chat_json mock] ✓ {result}")

print("\n所有 LLM 抽象层测试通过。真实 API 调用需要配置有效的 API Key。")
