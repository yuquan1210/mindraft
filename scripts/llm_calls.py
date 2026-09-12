"""Shared schema validation and single retry for analysis operations."""
import logging
from scripts.schemas import validate_llm_output


def call_with_retry(llm, system, user, schema):
    for attempt in range(2):
        try:
            result = llm.chat_json(system=system, user=user)
            valid, error = validate_llm_output(result, schema)
            if not valid:
                raise ValueError(error)
            return result
        except Exception:
            if attempt:
                raise
            logging.getLogger("mindraft").warning("LLM 调用或结构校验失败，自动重试一次")
