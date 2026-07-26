from scripts.llm.base import BaseLLM
from scripts.llm.kimi import KimiLLM
from scripts.llm.openai import OpenAILLM


def get_llm(config: dict) -> BaseLLM:
    """根据 config 中的 llm_provider 创建对应的 LLM 实现。"""
    provider = config["llm_provider"]
    match provider:
        case "kimi":
            return KimiLLM(config)
        case "openai":
            return OpenAILLM(config)
        case "anthropic":
            # 延迟导入 AnthropicLLM，避免未安装 anthropic 包时崩溃
            from scripts.llm.anthropic import AnthropicLLM
            return AnthropicLLM(config)
        case _:
            raise ValueError(f"未知的 LLM provider: {provider}")
