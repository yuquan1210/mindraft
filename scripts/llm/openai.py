import json
from openai import OpenAI
from .base import BaseLLM


class OpenAILLM(BaseLLM):
    """OpenAI LLM 实现。"""

    def __init__(self, config: dict):
        self.client = OpenAI(api_key=config["api_keys"]["openai"])
        self.model = config.get("llm_model", "gpt-4o")

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
