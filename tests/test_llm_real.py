"""Live smoke tests; unavailable credentials skip without breaking test collection."""
import pytest

from scripts.utils import load_config
from scripts.llm_factory import get_llm


@pytest.fixture(scope="module")
def llm():
    config = load_config()
    key = config.get("api_keys", {}).get(config["llm_provider"])
    if not key or key.startswith("${"):
        pytest.skip("Configured provider API key is not available in this process")
    return get_llm(config)


def test_real_chat(llm):
    response = llm.chat(system="你是一个友好的助手。请用一句话回答。",
                        user="你好，请简要介绍一下你自己。")
    assert isinstance(response, str) and response.strip()


def test_real_json(llm):
    response = llm.chat_json(system="你是一个 JSON 生成助手。",
                             user='请返回 {"greeting": "你好", "language": "中文"}，不要包含其他内容。')
    assert response.get("greeting") == "你好"
    assert response.get("language") == "中文"
