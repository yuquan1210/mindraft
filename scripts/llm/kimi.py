import json
from openai import OpenAI
from .base import BaseLLM


class KimiLLM(BaseLLM):
    """Kimi (Moonshot) LLM 实现，使用 OpenAI 兼容接口。"""

    def __init__(self, config: dict):
        self.client = OpenAI(
            api_key=config["api_keys"]["kimi"],
            base_url="https://api.kimi.com/coding/v1",
        )
        self.model = config.get("llm_model", "moonshot-v1-8k")

    def chat(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content

    def chat_json(self, system: str, user: str) -> dict:
        """使用原生 JSON 模式请求结构化输出，兜底处理 markdown 包裹。"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system + "\n\n请以 JSON 格式返回。"},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return self.extract_json(text)
