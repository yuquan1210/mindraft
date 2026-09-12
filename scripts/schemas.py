from jsonschema import validate, ValidationError
from scripts.memory_state import DOMAINS, LIST_PATHS, STRING_PATHS

# 拆分后单篇小笔记的结构（process_note 返回 notes 数组的 item）
NOTE_FRAGMENT_SCHEMA = {
    "type": "object",
    "required": ["title", "domain", "subcategory", "tags", "summary", "rewritten_content"],
    "properties": {
        "title": {"type": "string", "minLength": 1, "maxLength": 80},
        "domain": {
            "type": "string",
            "enum": list(DOMAINS),
        },
        "subcategory": {
            "type": "string",
            "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$",
            "maxLength": 40,
        },
        "tags": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$",
                "maxLength": 40,
            },
            "maxItems": 3,
        },
        "summary": {"type": "string", "maxLength": 60},
        "rewritten_content": {"type": "string", "minLength": 1},
    },
}

# Updates may only address a known leaf with the matching value type.
MEMORY_UPDATE_SCHEMA = {
    "type": "object", "required": ["action", "path", "value"],
    "oneOf": [
        {"properties": {"action": {"const": "APPEND_TO"}, "path": {"enum": list(LIST_PATHS)},
                        "value": {"type": "string", "minLength": 1}}},
        {"properties": {"action": {"const": "SET_IF_NEW"}, "path": {"enum": list(STRING_PATHS)},
                        "value": {"type": "string", "minLength": 1}}},
        {"properties": {"action": {"const": "SET_IF_NEW"}, "path": {"enum": list(LIST_PATHS)},
                        "value": {"type": "array", "items": {"type": "string"}}}},
    ],
    "additionalProperties": False,
    "properties": {"action": {}, "path": {}, "value": {}},
}

# process_note 操作的 LLM 返回结构：
# 一篇原笔记按内容类别拆分为 1~5 篇小笔记；memory_updates / questions 属于整篇原笔记
PROCESS_NOTE_SCHEMA = {
    "type": "object",
    "required": ["notes", "memory_updates"],
    "properties": {
        "notes": {
            "type": "array",
            "minItems": 1,
            "maxItems": 5,
            "items": NOTE_FRAGMENT_SCHEMA,
        },
        "questions": {"type": "array", "items": {"type": "string"}},
        "memory_updates": {
            "type": "array",
            "items": MEMORY_UPDATE_SCHEMA,
        },
    },
}

# Dashboard analyze 阶段 LLM 返回结构
DASHBOARD_SUMMARY_SCHEMA = {
    "type": "object",
    "required": [
        "daily_insight",
        "work_summary",
        "life_summary",
        "growth_summary",
        "wellbeing_summary",
        "identity_summary",
        "mbti_description",
    ],
    "properties": {
        "daily_insight": {"type": "string", "maxLength": 220},
        "work_summary": {"type": "string"},
        "life_summary": {"type": "string"},
        "growth_summary": {"type": "string"},
        "wellbeing_summary": {"type": "string"},
        "identity_summary": {"type": "string"},
        "mbti_description": {"type": "string", "minLength": 1},
    },
}


def validate_llm_output(data: dict, schema: dict) -> tuple[bool, str]:
    """校验 LLM 返回是否符合预期 schema，返回 (is_valid, error_message)"""
    try:
        validate(instance=data, schema=schema)
        return True, ""
    except ValidationError as e:
        return False, f"Schema validation failed: {e.message}"

COMPRESSION_SCHEMA = {
    "type": "object",
    "required": list(DOMAINS),
    "properties": {d: {"type": "string"} for d in DOMAINS},
    "additionalProperties": False,
}


# Accept legacy optional fields and additional state, but reject corrupt core types.
MEMORY_STATE_SCHEMA = {
    "type": "object", "required": ["meta", "active_memory"],
    "properties": {
        "meta": {"type": "object", "properties": {
            "processed_notes": {"type": "array", "items": {"type": "string"}},
            "version": {"type": "integer", "minimum": 0},
            "last_updated": {"type": "string"},
            "weekly_checkpoint": {"type": "string"},
        }},
        "active_memory": {"type": "object", "properties": {
            **{d: {"type": "object", "additionalProperties": {"oneOf": [
                {"type": "string"}, {"type": "array", "items": {"type": "string"}}
            ]}} for d in DOMAINS},
            "_condensed": COMPRESSION_SCHEMA,
        }},
        "history_archive": {"type": "array", "items": {"type": "object"}},
        "tag_candidates": {"type": "object", "additionalProperties": {
            "type": "object", "required": ["count", "status"], "properties": {
                "count": {"type": "integer", "minimum": 0},
                "status": {"enum": ["pending", "active"]},
            }}},
    },
}
