# scripts/process_notes.py
import json
import logging
import re
from datetime import datetime
from pathlib import Path

import yaml

from scripts.llm_factory import get_llm
from scripts.schemas import PROCESS_NOTE_SCHEMA, validate_llm_output
from scripts.prompts import NOTE_PROCESSOR_ROLE
from scripts.skill_loader import build_system_prompt
from scripts.note_filter import should_skip_note, group_notes_for_processing
from scripts.utils import (
    safe_write_json,
    token_estimate,
    today_iso,
    get_memory_path,
    get_nested,
    set_nested,
    exists_nested,
    is_semantically_duplicate,
)

logger = logging.getLogger("mindraft")


def create_initial_memory() -> dict:
    """创建初始 memory.json 结构（五域硬编码）。"""
    return {
        "meta": {
            "version": 0,
            "last_updated": "",
            "processed_notes": [],
            "active_memory_token_estimate": 0,
        },
        "active_memory": {
            "work": {
                "current_focus": "",
                "ongoing_projects": [],
                "goals": [],
                "energy_pattern": "",
                "stress_sources": [],
                "recurring_signals": [],
                "recent_mood_trend": "",
            },
            "life": {
                "current_routines": [],
                "interests_observed": [],
                "social_connections": [],
                "places": [],
                "important_people": [],
                "recurring_signals": [],
                "recent_mood_trend": "",
            },
            "growth": {
                "learning_topics": [],
                "active_skills": [],
                "challenges": [],
                "recurring_signals": [],
            },
            "wellbeing": {
                "physical_patterns": [],
                "mental_patterns": [],
                "recovery_activities": [],
                "recurring_signals": [],
            },
            "identity": {
                "core_traits": [],
                "values": [],
                "self_perception": [],
                "mbti_hints": [],
                "recurring_signals": [],
            },
        },
        "tag_candidates": {},
        "history_archive": [],
    }


def process_new_notes(config: dict, dry_run: bool = False):
    """处理 raw_notes 中的新笔记。"""
    vault = Path(config["notes_vault_path"]).expanduser()
    memory_path = get_memory_path(config)
    memory = create_initial_memory()
    if memory_path.exists():
        memory = json.loads(memory_path.read_text(encoding="utf-8"))

    llm = get_llm(config)
    token_method = config.get("token_estimation", "char_ratio")

    processed = set(memory["meta"]["processed_notes"])
    all_notes = sorted(vault.glob("raw_notes/*.md"))
    new_notes = []
    skipped = []

    for note_path in all_notes:
        if note_path.name in processed:
            continue
        content = note_path.read_text(encoding="utf-8")
        skip, reason = should_skip_note(content, config)
        if skip:
            skipped.append({"name": note_path.name, "reason": reason})
            memory["meta"]["processed_notes"].append(note_path.name)
            logger.info(f"跳过笔记 {note_path.name}：{reason}")
            continue
        new_notes.append({"name": note_path.name, "content": content, "path": note_path})

    if not new_notes:
        logger.info("没有新的有效笔记需要处理")
        if skipped and not dry_run:
            safe_write_json(str(memory_path), memory)
        return

    # 先保存被跳过的笔记标记，避免丢失
    if skipped and not dry_run:
        safe_write_json(str(memory_path), memory)

    groups = group_notes_for_processing(new_notes, config)
    logger.info(f"待处理 {len(new_notes)} 篇笔记，分为 {len(groups)} 组")

    for group in groups:
        # Phase 1 每组只有一篇笔记
        note = group[0]
        try:
            result = _call_with_retry(note, memory, llm, config)

            if dry_run:
                logger.info(f"[DRY-RUN] 将处理 {note['name']} → {result['category']}")
                continue

            write_ai_note(vault, note["name"], result)
            apply_memory_updates(memory["active_memory"], result.get("memory_updates", []))
            update_tag_candidates(memory, result.get("tags", []))
            memory["meta"]["processed_notes"].append(note["name"])
            memory["meta"]["last_updated"] = today_iso()
            memory["meta"]["version"] += 1
            memory["meta"]["active_memory_token_estimate"] = token_estimate(
                json.dumps(memory["active_memory"], ensure_ascii=False), token_method
            )
            safe_write_json(str(memory_path), memory)
            logger.info(f"✓ 已处理 {note['name']} → {result['category']}")
        except Exception as e:
            logger.error(f"处理笔记 {note['name']} 失败：{_friendly_error(e)}（已跳过该笔记，下次运行时会重新处理）")
            continue


def process_single_note(note: dict, memory: dict, llm, config: dict) -> dict:
    """调用 LLM 处理单篇笔记。"""
    system = build_system_prompt("process_note", NOTE_PROCESSOR_ROLE, config)
    user_content = f"""用户历史记忆摘要（active_memory）：
{json.dumps(memory['active_memory'], ensure_ascii=False, indent=2)}

请处理以下原始笔记：
文件名：{note['name']}

内容：
{note['content']}"""
    return llm.chat_json(system=system, user=user_content)


def _call_with_retry(note: dict, memory: dict, llm, config: dict) -> dict:
    """调用 LLM 处理单篇笔记并校验返回，失败时重试一次。"""
    last_error = None
    for attempt in range(2):
        try:
            result = process_single_note(note, memory, llm, config)
            is_valid, error = validate_llm_output(result, PROCESS_NOTE_SCHEMA)
            if not is_valid:
                raise ValueError(error)
            # LLM 返回 domain + subcategory，join 为 category 供下游使用
            result["category"] = f"{result['domain']}/{result['subcategory']}"
            return result
        except Exception as e:
            last_error = e
            if attempt == 0:
                logger.warning(f"笔记 {note['name']} 首次处理失败（{_friendly_error(e)}），自动重试一次")
    raise last_error


def _friendly_error(e: Exception) -> str:
    """将底层异常翻译成易读的中文说明。"""
    msg = str(e)
    if isinstance(e, json.JSONDecodeError) or "Invalid control character" in msg or "Expecting" in msg:
        return f"LLM 返回的内容不是合法 JSON（{msg}）"
    if msg.startswith("Schema validation failed"):
        return f"LLM 返回的字段不符合格式要求（{msg}）"
    return msg


def apply_memory_updates(active_memory: dict, updates: list):
    """应用 LLM 返回的记忆更新指令。"""
    for update in updates:
        action = update.get("action")
        path = update.get("path")
        value = update.get("value")

        if action == "APPEND_TO":
            target = get_nested(active_memory, path)
            if not isinstance(target, list):
                logger.warning(
                    f"已忽略一条记忆更新：APPEND_TO 目标 {path} 在 active_memory 中不存在或不是列表"
                    f"（LLM 可能自创了路径或写错域前缀）"
                )
                continue
            if isinstance(value, str) and is_semantically_duplicate(value, target):
                continue
            if value not in target:
                target.append(value)
        elif action == "SET_IF_NEW":
            if not exists_nested(active_memory, path):
                set_nested(active_memory, path, value)
            else:
                current = get_nested(active_memory, path)
                if not current:
                    set_nested(active_memory, path, value)
        else:
            logger.warning(f"已忽略一条记忆更新：action={action} 非法（只允许 APPEND_TO / SET_IF_NEW）")


class _FlowList(list):
    """标记类：强制 YAML 以 flow 风格（inline array）序列化，用于 frontmatter tags。"""


class _FrontmatterDumper(yaml.SafeDumper):
    """frontmatter 专用 Dumper，避免污染全局 yaml 配置。"""


_FrontmatterDumper.add_representer(
    _FlowList,
    lambda dumper, data: dumper.represent_sequence(
        "tag:yaml.org,2002:seq", data, flow_style=True
    ),
)


def write_ai_note(vault: Path, raw_name: str, result: dict):
    """将重写后的笔记写入 ai_notes/ 目录。"""
    category = result["category"]
    title = result["title"]
    slug = title_to_slug(title)

    target_dir = vault / "ai_notes" / category
    target_dir.mkdir(parents=True, exist_ok=True)

    base_path = target_dir / f"{slug}.md"
    target_path = base_path
    counter = 2
    while target_path.exists():
        target_path = target_dir / f"{slug}-{counter}.md"
        counter += 1

    frontmatter = {
        "title": title,
        "processed_at": datetime.now().isoformat(timespec="seconds"),
        "category": category,
        "tags": _FlowList(result.get("tags", [])),
        "summary": result.get("summary", ""),
        "source": f"raw_notes/{raw_name}",
    }

    content = "---\n"
    content += yaml.dump(
        frontmatter, Dumper=_FrontmatterDumper, allow_unicode=True, sort_keys=False
    )
    content += "---\n\n"
    content += result["rewritten_content"]

    target_path.write_text(content, encoding="utf-8")


def update_tag_candidates(memory: dict, tags: list):
    """更新 tag 候选统计。Phase 1 只累计 count，不升级。"""
    candidates = memory.setdefault("tag_candidates", {})
    tag_pattern = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
    for tag in tags:
        if not tag_pattern.match(tag):
            logger.warning(f"已忽略候选 tag {tag}：格式非法（要求英文小写连字符，如 system-design）")
            continue
        if tag not in candidates:
            candidates[tag] = {"count": 0, "status": "pending"}
        candidates[tag]["count"] += 1


def title_to_slug(title: str) -> str:
    """将英文标题转换为文件名 slug。"""
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug or "untitled"
