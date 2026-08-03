# scripts/note_filter.py
import logging
import re
from pathlib import Path

logger = logging.getLogger("mindraft")


def should_skip_note(content: str, config: dict) -> tuple[bool, str]:
    """判断笔记是否应该跳过处理，返回 (should_skip, reason)"""
    filter_config = config.get("note_filter", {})

    # 空文件
    stripped = content.strip()
    if not stripped:
        return True, "empty_file"

    # 低于最小有意义字符数
    min_chars = filter_config.get("min_meaningful_chars", 20)
    if len(stripped) < min_chars:
        return True, f"too_short ({len(stripped)} chars < {min_chars})"

    # 仅包含无法理解的代码片段（无自然语言文字）
    natural_text = re.sub(r"```[\s\S]*?```", "", stripped)   # 去掉代码块
    natural_text = re.sub(r"`[^`]+`", "", natural_text)      # 去掉行内代码
    natural_text = re.sub(r"[^\w\s\u4e00-\u9fff]", "", natural_text)  # 去掉符号
    natural_text = natural_text.strip()
    if len(natural_text) < 10:
        return True, "no_meaningful_natural_language"

    return False, ""


def group_notes_for_processing(notes: list[dict], config: dict) -> list[list[dict]]:
    """
    将笔记按处理方式分组。
    Phase 1 暂时不做 batching，每篇笔记独立处理。
    保留接口给未来 batching 优化。
    """
    return [[n] for n in notes]
