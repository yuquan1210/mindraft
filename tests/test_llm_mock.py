"""Provider-independent, collected tests; never depend on the user's live config."""
import json
from unittest.mock import Mock, patch

import pytest
from scripts.llm.base import BaseLLM
from scripts.llm_factory import get_llm


def test_extract_json_control_characters():
    parsed = BaseLLM.extract_json('{"rewritten_content": "line1\nline2"}')
    assert parsed['rewritten_content'] == 'line1\nline2'


@pytest.mark.parametrize('provider', ['openai', 'kimi', 'deepseek'])
def test_provider_chat_and_json(provider):
    config = {'llm_provider': provider, 'api_keys': {provider: 'test-key'}}
    response = Mock()
    response.choices = [Mock(message=Mock(content='模拟响应'))]
    with patch(f'scripts.llm.{provider}.OpenAI') as client:
        client.return_value.chat.completions.create.return_value = response
        llm = get_llm(config)
        assert llm.chat(system='test', user='hello') == '模拟响应'
        payload = {'greeting': '你好'}
        response.choices[0].message.content = f'```json\n{json.dumps(payload)}\n```'
        assert llm.chat_json(system='test', user='json') == payload
