import json
from openai import OpenAI
from .base import BaseLLM


class DeepSeekLLM(BaseLLM):
    """DeepSeek LLM 实现，使用 OpenAI 兼容接口。"""

    def __init__(self, config: dict):
        self.client = OpenAI(
            api_key=config["api_keys"]["deepseek"],
            base_url="https://api.deepseek.com",
        )
        self.model = config.get("llm_model", "deepseek-v4-flash")
        self.reasoning_effort = config.get("llm_reasoning_effort", "high")

    def _extra_body(self) -> dict | None:
        """根据 llm_reasoning_effort 配置构建 DeepSeek 思考模式参数。"""
        effort = self.reasoning_effort
        if effort in (None, "", "none"):
            return {"thinking": {"type": "disabled"}}
        return {"reasoning_effort": effort}

    def chat(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            extra_body=self._extra_body(),
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
            extra_body=self._extra_body(),
        )
        text = response.choices[0].message.content
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return self.extract_json(text)
