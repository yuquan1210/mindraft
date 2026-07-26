import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils import load_config
from scripts.llm_factory import get_llm

config = load_config()
llm = get_llm(config)

# 真实文本对话测试
response = llm.chat(
    system="你是一个友好的助手。请用一句话回答。",
    user="你好，请简要介绍一下你自己。",
)
print(f"[chat response] {response}")

# 真实 JSON 模式测试
json_response = llm.chat_json(
    system="你是一个 JSON 生成助手。",
    user='请以 JSON 格式返回 {"greeting": "你好", "language": "中文"}，不要包含其他内容。',
)
print(f"[chat_json response] {json_response}")

assert isinstance(json_response, dict)
assert json_response.get("greeting") == "你好"
assert json_response.get("language") == "中文"
print("真实 LLM API 调用测试通过")
