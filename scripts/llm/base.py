from abc import ABC, abstractmethod
import json
import re


class BaseLLM(ABC):
    """LLM 抽象基类。所有业务代码只依赖此接口，不直接引用具体模型实现。"""

    @abstractmethod
    def chat(self, system: str, user: str) -> str:
        """发送对话请求，返回文本响应"""
        pass

    @abstractmethod
    def chat_json(self, system: str, user: str) -> dict:
        """发送请求，使用原生 JSON 模式，返回解析后的 JSON"""
        pass

    @staticmethod
    def extract_json(text: str) -> dict:
        """从 LLM 返回文本中提取 JSON（兜底解析：去除 markdown 代码块包裹）"""
        cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            # 低思考模式下模型可能在字符串值内输出未转义的控制字符（换行/制表符），
            # strict=False 容忍字符串内的控制字符后再解析
            return json.loads(cleaned, strict=False)
