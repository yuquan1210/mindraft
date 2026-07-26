from jsonschema import validate, ValidationError

# process_note 操作的 LLM 返回结构
PROCESS_NOTE_SCHEMA = {
    "type": "object",
    "required": ["category", "tags", "summary", "rewritten_content", "memory_updates"],
    "properties": {
        "category": {"type": "string", "pattern": "^(work|life|study)/"},
        "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "summary": {"type": "string", "maxLength": 60},
        "rewritten_content": {"type": "string", "minLength": 1},
        "questions": {"type": "array", "items": {"type": "string"}},
        "related_notes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["path", "strength", "reason"],
                "properties": {
                    "path": {"type": "string"},
                    "strength": {"type": "string", "enum": ["high", "medium"]},
                    "reason": {"type": "string"},
                },
            },
        },
        "memory_updates": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["action", "path", "value"],
                "properties": {
                    "action": {"type": "string"},
                    "path": {"type": "string"},
                    "value": {},
                },
            },
        },
    },
}

# 批量处理多篇笔记时的返回结构
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


def validate_llm_output(data: dict, schema: dict) -> tuple[bool, str]:
    """校验 LLM 返回是否符合预期 schema，返回 (is_valid, error_message)"""
    try:
        validate(instance=data, schema=schema)
        return True, ""
    except ValidationError as e:
        return False, f"Schema validation failed: {e.message}"
