from jsonschema import validate, ValidationError

# process_note 操作的 LLM 返回结构
PROCESS_NOTE_SCHEMA = {
    "type": "object",
    "required": ["title", "domain", "subcategory", "tags", "summary", "rewritten_content", "memory_updates"],
    "properties": {
        "title": {"type": "string", "minLength": 1, "maxLength": 80},
        "domain": {
            "type": "string",
            "enum": ["work", "life", "growth", "wellbeing", "identity"],
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
        "questions": {"type": "array", "items": {"type": "string"}},
        "memory_updates": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["action", "path", "value"],
                "properties": {
                    "action": {"type": "string", "enum": ["APPEND_TO", "SET_IF_NEW"]},
                    "path": {"type": "string"},
                    "value": {},
                },
            },
        },
    },
}

# 批量处理多篇笔记时的返回结构（Phase 1 不使用，保留接口）
BATCH_PROCESS_SCHEMA = {
    "type": "object",
    "required": ["notes"],
    "properties": {
        "notes": {
            "type": "array",
            "items": PROCESS_NOTE_SCHEMA,
        }
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
    ],
    "properties": {
        "daily_insight": {"type": "string", "maxLength": 220},
        "work_summary": {"type": "string"},
        "life_summary": {"type": "string"},
        "growth_summary": {"type": "string"},
        "wellbeing_summary": {"type": "string"},
        "identity_summary": {"type": "string"},
    },
}


def validate_llm_output(data: dict, schema: dict) -> tuple[bool, str]:
    """校验 LLM 返回是否符合预期 schema，返回 (is_valid, error_message)"""
    try:
        validate(instance=data, schema=schema)
        return True, ""
    except ValidationError as e:
        return False, f"Schema validation failed: {e.message}"
