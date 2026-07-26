import json
from .base import BaseLLM


class AnthropicLLM(BaseLLM):
    """Anthropic Claude LLM 实现。依赖 anthropic Python 包，使用时按需安装。"""

    def __init__(self, config: dict):
        try:
            from anthropic import Anthropic
        except ImportError as e:
            raise ImportError(
                "Anthropic provider 需要安装 anthropic 包。运行: pip install anthropic"
            ) from e

        self.client = Anthropic(api_key=config["api_keys"]["anthropic"])
        self.model = config.get("llm_model", "claude-3-5-sonnet-20241022")

    def chat(self, system: str, user: str) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text

    def chat_json(self, system: str, user: str) -> dict:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system + "\n\n请以 JSON 格式返回。",
            messages=[{"role": "user", "content": user}],
        )
        text = response.content[0].text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return self.extract_json(text)
