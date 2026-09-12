"""Shared memory structure and fail-closed loading for processing and analysis."""
import json
from pathlib import Path

DOMAINS = ("work", "life", "growth", "wellbeing", "identity")


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


MEMORY_FIELDS = create_initial_memory()["active_memory"]
LIST_PATHS = tuple(f"{domain}.{field}" for domain, fields in MEMORY_FIELDS.items()
                   for field, value in fields.items() if isinstance(value, list))
STRING_PATHS = tuple(f"{domain}.{field}" for domain, fields in MEMORY_FIELDS.items()
                     for field, value in fields.items() if isinstance(value, str))


def load_memory(path: Path) -> dict:
    """Missing state is new; unreadable or malformed state must never become empty memory."""
    from scripts.schemas import MEMORY_STATE_SCHEMA, validate_llm_output

    if not path.exists():
        legacy = path.parent.parent / "analysis" / "memory.json"
        if path.parent.name == ".mindraft" and legacy.exists():
            path = legacy  # dry-run can read legacy state without moving it.
        else:
            return create_initial_memory()
    try:
        memory = json.loads(path.read_text(encoding="utf-8"))
        valid, error = validate_llm_output(memory, MEMORY_STATE_SCHEMA)
        if not valid:
            raise ValueError(error)
    except (OSError, ValueError) as exc:
        raise ValueError(f"无法读取记忆状态 {path}；保留原文件，请检查或从备份恢复。") from exc
    # Older files may omit metadata added later. Add only absent fields.
    for key, value in create_initial_memory()["meta"].items():
        memory["meta"].setdefault(key, value)
    memory.setdefault("tag_candidates", {})
    memory.setdefault("history_archive", [])
    return memory
