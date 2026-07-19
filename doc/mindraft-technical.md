# Mindraft — 技术参考文档

> 包含所有模块的代码示例和数据结构定义，供实现阶段参考。
> 产品概览：[# Mindraft.md](# Mindraft.md) · 实现日志：[Mindraft-Log.md](Mindraft-Log.md)

---

## 目录

1. [配置文件 config.yml](#1-配置文件-configyml)
2. [LLM 抽象层](#2-llm-抽象层)
3. [Skill 配置文件](#3-skill-配置文件)
4. [skill_loader.py](#4-skill_loaderpy)
5. [笔记处理](#5-笔记处理)
6. [记忆系统](#6-记忆系统)
7. [用户形象系统](#7-用户形象系统)
8. [Dashboard 前端](#8-dashboard-前端)
9. [数据结构参考](#9-数据结构参考)
10. [run.py 实现](#10-runpy-实现)
11. [UI 样式](#11-ui-样式)

---

## 1. 配置文件 config.yml

```yaml
# 笔记仓库路径（指向 notes-vault 本地路径）
notes_vault_path: ~/Documents/notes-vault

# LLM 配置（改 llm_provider 这一行切换模型）
llm_provider: deepseek       # deepseek | openai | anthropic
llm_model: deepseek-chat

# API Keys（建议用环境变量，此处为占位）
api_keys:
  deepseek:  ${DEEPSEEK_API_KEY}
  openai:    ${OPENAI_API_KEY}
  anthropic: ${ANTHROPIC_API_KEY}
  replicate: ${REPLICATE_API_KEY}

# 记忆压缩阈值（估算 token 数）
memory:
  active_memory_token_threshold: 1500
  compression_target_ratio: 0.55

# Skill 开关
skills:
  note_style:
    enabled: true
  summary_style:
    enabled: true
  tagging:
    enabled: true
  analysis_style:
    enabled: true
  memory_compression:
    enabled: true

# 笔记预筛选
note_filter:
  skip_empty: true                    # 跳过空文件
  min_meaningful_chars: 20            # 低于此字符数视为无意义笔记
  batch_short_notes: true             # 将短笔记合并为一次 LLM 调用
  batch_max_notes: 5                  # 单次批量处理最大笔记数
  batch_char_threshold: 200           # 单篇低于此字符数视为"短笔记"，可合并

# 日志配置
logging:
  level: INFO                         # DEBUG | INFO | WARNING | ERROR
  file: analysis/process_log.jsonl    # 日志输出路径（相对于 notes_vault_path）

# Token 估算方式
token_estimation: char_ratio           # char_ratio（字符数 / 2）| tiktoken

# 用户画像渲染配置（改 renderer 这一行切换渲染器）
avatar:
  renderer: text_card       # text_card | pixel_art | animated_sprite | game
  work_scene: studio
  home_scene: home

# Dashboard 本地服务端口
dashboard_port: 8080
```

---

## 2. LLM 抽象层

### llm/base.py

```python
from abc import ABC, abstractmethod
import json
import re

class BaseLLM(ABC):
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
        cleaned = re.sub(r'^```(?:json)?\s*', '', text.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned)
        return json.loads(cleaned)
```

### llm/deepseek.py

```python
from openai import OpenAI
from .base import BaseLLM
import json

class DeepSeekLLM(BaseLLM):
    def __init__(self, config: dict):
        self.client = OpenAI(
            api_key=config["api_keys"]["deepseek"],
            base_url="https://api.deepseek.com"
        )
        self.model = config.get("llm_model", "deepseek-chat")

    def chat(self, system: str, user: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ]
        )
        return response.choices[0].message.content

    def chat_json(self, system: str, user: str) -> dict:
        """使用原生 JSON 模式请求结构化输出，兜底处理 markdown 包裹"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system + "\n\n请以 JSON 格式返回。"},
                {"role": "user", "content": user}
            ],
            response_format={"type": "json_object"}
        )
        text = response.choices[0].message.content
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return self.extract_json(text)
```

### llm_factory.py

```python
from scripts.llm.deepseek import DeepSeekLLM
from scripts.llm.openai import OpenAILLM
from scripts.llm.anthropic import AnthropicLLM
from scripts.llm.base import BaseLLM

def get_llm(config: dict) -> BaseLLM:
    provider = config["llm_provider"]
    match provider:
        case "deepseek":   return DeepSeekLLM(config)
        case "openai":     return OpenAILLM(config)
        case "anthropic":  return AnthropicLLM(config)
        case _:            raise ValueError(f"未知的 LLM provider: {provider}")
```

---

## 3. Skill 配置文件

### skills/note_style.yml

```yaml
name: note_style
description: "笔记重写与内容规范"
applies_to:
  - process_note
  - enrich_with_link
rules:
  - "核心任务：将原始笔记重写为清晰、结构化的版本，保留所有核心信息，补充可合理推断的背景知识"
  - "语言风格：简单、清晰、易懂，避免术语堆砌；必须使用专业术语时，第一次出现时括号内简短解释"
  - "代码必须使用 markdown 代码块，并标注语言类型，例如 ```python"
  - "输出格式为标准 markdown，使用标题、列表、代码块等结构"
  - "笔记中包含 URL 时，追加对应页面的内容摘要，格式：> 📎 [标题](url)：摘要内容"
  - "无法从已有知识或笔记上下文推断的内容，添加注释：<!-- ❓ 待补充：[具体问题]，请作者补充更多信息。 -->"
  - "严禁凭空添加任何未在原文中出现且无法合理推断的事实，宁可留空 + 追问，不可胡编乱造"
```

### skills/summary_style.yml

```yaml
name: summary_style
description: "每日一句话摘要的风格"
applies_to:
  - generate_daily_summary
rules:
  - "每篇笔记生成一句话摘要，20 字以内"
  - "语气像朋友之间说话，不要正式或书面"
  - "聚焦今天最重要的一件事或一个状态"
  - "中文输出"
```

### skills/tagging.yml

```yaml
name: tagging
description: "tag 候选生成规则"
applies_to:
  - process_note
rules:
  - "每篇笔记最多提出 3 个候选 tag"
  - "tag 使用英文小写，多个单词用连字符，例如 system-design"
  - "tag 代表主题或领域，不代表情绪或时间，禁止使用 today / feeling-good 等"
  - "只提候选，不直接写入笔记，由系统判断是否满足 3 篇阈值后正式创建"
```

### skills/analysis_style.yml

```yaml
name: analysis_style
description: "用户画像和 MBTI 风格分析的输出风格"
applies_to:
  - generate_profile
  - generate_mbti_description
  - generate_avatar_data
rules:
  - "语气温和，像一位了解你的老朋友在描述你"
  - "不做负面评判，观察即描述，不贴标签"
  - "指出矛盾或变化时，使用'有趣的是...'或'值得注意的是...'"
  - "中文输出，适当保留英文专有名词"
  - "描述长度：3-5 段，每段 2-4 句话"
```

### skills/memory_compression.yml

```yaml
name: memory_compression
description: "压缩 active_memory 时的行为规则"
applies_to:
  - compress_memory
rules:
  - "只能精简表达，不能删除任何独特的观察或信号"
  - "合并表达相同意思的条目，保留最完整的版本"
  - "如果两条内容互相矛盾，两条都保留，并追加一条标注：'存在矛盾信号'"
  - "压缩后 token 量应控制在原来的 50%-60%"
```

---

## 4. skill_loader.py

```python
# scripts/skill_loader.py
import yaml
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills"

def build_system_prompt(operation: str, base_role: str, config: dict) -> str:
    """
    根据 operation 名称，自动查找所有适用且启用的 skill，
    拼装为完整的 system prompt
    """
    skill_toggles = config.get("skills", {})
    applicable_rules = []

    for skill_file in sorted(SKILLS_DIR.glob("*.yml")):
        skill = yaml.safe_load(skill_file.read_text())
        skill_name = skill.get("name")

        if not skill_toggles.get(skill_name, {}).get("enabled", True):
            continue

        if operation in skill.get("applies_to", []):
            rules_text = "\n".join(f"- {r}" for r in skill["rules"])
            applicable_rules.append(
                f"### {skill['description']}\n{rules_text}"
            )

    if not applicable_rules:
        return base_role

    rules_block = "\n\n".join(applicable_rules)
    return f"{base_role}\n\n## 执行规则\n\n{rules_block}"
```

---

## 5. 笔记处理

### 5.0 角色定义（Base Role Prompts）

所有 LLM 调用的 `base_role` 参数在此统一定义。`build_system_prompt()` 在此基础上追加 skill 规则。

```python
# scripts/prompts.py

NOTE_PROCESSOR_ROLE = """你是 Mindraft 笔记处理助手。
你的任务是阅读用户的原始笔记，将其重写为清晰、结构化的版本。
你会收到用户的历史记忆摘要（active_memory），用于理解上下文。
你必须以 JSON 格式返回处理结果。
严禁杜撰任何事实。无法推断的内容必须用追问标记，不可猜测。"""

COMPRESSOR_ROLE = """你是 Mindraft 记忆压缩助手。
你的任务是精简 active_memory 的表达，同时保留所有独特的观察和信号。
你只能合并重复表达，不能删除任何有价值的信息。
如果两条内容互相矛盾，两条都保留。
你必须以 JSON 格式返回压缩后的 active_memory。"""

ANALYZER_ROLE = """你是 Mindraft 用户画像分析助手。
你的任务是基于用户的记忆数据，生成或更新用户的自我画像。
语气温和，像一位了解用户的老朋友在描述他。
不做负面评判，观察即描述。中文输出。"""

PROFILE_ROLE = """你是 Mindraft 性格分析助手。
你的任务是基于用户近期的记忆数据，生成一段 MBTI 风格的性格描述。
不是给出 MBTI 类型标签，而是用文学化的语言描述用户的状态和特点。
中文输出，3-5 段，每段 2-4 句话。"""
```

### 5.1 LLM 返回结构 + JSON Schema 校验

```python
# scripts/schemas.py
from jsonschema import validate, ValidationError

# process_note 操作的 LLM 返回结构
PROCESS_NOTE_SCHEMA = {
    "type": "object",
    "required": ["category", "tags", "summary", "rewritten_content", "memory_updates"],
    "properties": {
        "category":          {"type": "string", "pattern": "^(work|life|study)/"},
        "tags":              {"type": "array", "items": {"type": "string"}, "maxItems": 3},
        "summary":           {"type": "string", "maxLength": 60},
        "rewritten_content": {"type": "string", "minLength": 1},
        "questions":         {"type": "array", "items": {"type": "string"}},
        "related_notes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["path", "strength", "reason"],
                "properties": {
                    "path":     {"type": "string"},
                    "strength": {"type": "string", "enum": ["high", "medium"]},
                    "reason":   {"type": "string"}
                }
            }
        },
        "memory_updates": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["action", "path", "value"],
                "properties": {
                    "action": {"type": "string"},
                    "path":   {"type": "string"},
                    "value":  {}
                }
            }
        }
    }
}

# 批量处理多篇笔记时的返回结构
BATCH_PROCESS_SCHEMA = {
    "type": "object",
    "required": ["notes"],
    "properties": {
        "notes": {
            "type": "array",
            "items": PROCESS_NOTE_SCHEMA
        }
    }
}

def validate_llm_output(data: dict, schema: dict) -> tuple[bool, str]:
    """校验 LLM 返回是否符合预期 schema，返回 (is_valid, error_message)"""
    try:
        validate(instance=data, schema=schema)
        return True, ""
    except ValidationError as e:
        return False, f"Schema validation failed: {e.message}"
```

### 5.2 笔记预筛选与批量合并

```python
# scripts/note_filter.py

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
    import re
    natural_text = re.sub(r'```[\s\S]*?```', '', stripped)   # 去掉代码块
    natural_text = re.sub(r'`[^`]+`', '', natural_text)      # 去掉行内代码
    natural_text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', natural_text)  # 去掉符号
    natural_text = natural_text.strip()
    if len(natural_text) < 10:
        return True, "no_meaningful_natural_language"

    return False, ""


def group_notes_for_processing(notes: list[dict], config: dict) -> list[list[dict]]:
    """
    将笔记按处理方式分组：
    - 短笔记合并为一批（一次 LLM 调用处理多篇）
    - 长笔记各自独立处理
    返回：[[note1, note2, ...], [note3], [note4], ...]
    """
    filter_config = config.get("note_filter", {})
    batch_enabled = filter_config.get("batch_short_notes", True)
    char_threshold = filter_config.get("batch_char_threshold", 200)
    max_batch = filter_config.get("batch_max_notes", 5)

    if not batch_enabled:
        return [[n] for n in notes]

    short_notes, long_notes = [], []
    for note in notes:
        if len(note["content"]) <= char_threshold:
            short_notes.append(note)
        else:
            long_notes.append(note)

    groups = []
    # 短笔记分批
    for i in range(0, len(short_notes), max_batch):
        groups.append(short_notes[i:i + max_batch])
    # 长笔记各自独立
    for note in long_notes:
        groups.append([note])

    return groups
```

### 5.3 核心工具函数

```python
# scripts/utils.py
import json
import os
import tempfile
import logging
from pathlib import Path
from filelock import FileLock
from datetime import datetime

logger = logging.getLogger("mindraft")

# ── Token 估算 ──────────────────────────────────────────
def token_estimate(text: str, method: str = "char_ratio") -> int:
    """
    估算文本 token 数。
    - char_ratio：中文按 字符数/1.5 估算，英文按 字符数/4 估算，混合取加权平均
    - tiktoken：使用 tiktoken 库精确计算（需安装 tiktoken）
    """
    if method == "tiktoken":
        import tiktoken
        enc = tiktoken.encoding_for_model("gpt-4")
        return len(enc.encode(text))

    # char_ratio 模式：中文字符 ≈ 1.5 token，英文 ≈ 4 chars/token
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars / 1.5 + other_chars / 4)


# ── 语义去重 ──────────────────────────────────────────
def is_semantically_duplicate(new_value: str, existing_list: list[str]) -> bool:
    """
    判断新值是否与已有列表中的某条语义重复。
    采用简单字符串相似度：如果新值与任一已有值的共同字符占比 > 70%，视为重复。
    Phase 3+ 可替换为 embedding 向量余弦相似度。
    """
    if not isinstance(new_value, str):
        return new_value in existing_list

    new_norm = new_value.strip().lower()
    for existing in existing_list:
        if not isinstance(existing, str):
            continue
        existing_norm = existing.strip().lower()
        # 完全包含
        if new_norm in existing_norm or existing_norm in new_norm:
            return True
        # 字符级 Jaccard 相似度
        set_new = set(new_norm)
        set_existing = set(existing_norm)
        intersection = set_new & set_existing
        union = set_new | set_existing
        if union and len(intersection) / len(union) > 0.7:
            return True
    return False


# ── 原子写入 ──────────────────────────────────────────
def safe_write_json(filepath: str, data: dict):
    """
    原子写入 JSON 文件：先写临时文件，再 rename。
    防止写入中途崩溃导致文件损坏。
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=filepath.parent, suffix=".tmp", prefix=filepath.stem
    )
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)
    except Exception:
        os.unlink(tmp_path)
        raise


# ── 进程锁 ──────────────────────────────────────────
def get_process_lock(notes_vault_path: str) -> FileLock:
    """获取进程级文件锁，防止并发执行"""
    lock_path = Path(notes_vault_path) / "analysis" / ".mindraft.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(lock_path), timeout=10)


# ── 日志初始化 ──────────────────────────────────────────
def setup_logging(config: dict):
    """初始化日志系统，输出到文件 + 控制台"""
    log_config = config.get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO"))
    log_file = Path(config["notes_vault_path"]) / log_config.get(
        "file", "analysis/process_log.jsonl"
    )
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("mindraft")
    logger.setLevel(level)

    # 控制台：简洁格式
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console)

    # 文件：JSONL 格式，便于程序解析
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(
        '{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}'
    ))
    logger.addHandler(file_handler)

    return logger
```

### 5.4 笔记处理主逻辑（含逐篇 checkpoint + 失败恢复）

```python
# scripts/process_notes.py（核心流程）

def process_new_notes(config: dict, dry_run: bool = False):
    logger = logging.getLogger("mindraft")
    vault = Path(config["notes_vault_path"]).expanduser()
    memory_path = vault / "analysis" / "memory.json"
    memory = json.loads(memory_path.read_text()) if memory_path.exists() else create_initial_memory()
    llm = get_llm(config)
    token_method = config.get("token_estimation", "char_ratio")

    # 1. 扫描未处理的笔记（按日期升序排列）
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
            # 跳过的笔记也标记为已处理，避免每次重复扫描
            memory["meta"]["processed_notes"].append(note_path.name)
            logger.info(f"跳过笔记 {note_path.name}：{reason}")
            continue
        new_notes.append({"name": note_path.name, "content": content, "path": note_path})

    if not new_notes:
        logger.info("没有新的有效笔记需要处理")
        if skipped and not dry_run:
            safe_write_json(str(memory_path), memory)
        return

    # 2. 分组：短笔记合并，长笔记独立
    groups = group_notes_for_processing(new_notes, config)
    logger.info(f"待处理 {len(new_notes)} 篇笔记，分为 {len(groups)} 组")

    # 3. 逐组处理（每组处理完立即持久化，实现断点恢复）
    for group in groups:
        try:
            if len(group) == 1:
                result = process_single_note(group[0], memory, llm, config)
                results = [result]
            else:
                results = process_batch_notes(group, memory, llm, config)

            for note, result in zip(group, results):
                if dry_run:
                    logger.info(f"[DRY-RUN] 将处理 {note['name']} → {result['category']}")
                    continue

                # 写入 ai_notes
                write_ai_note(vault, note["name"], result)
                # 更新记忆
                apply_memory_updates(memory["active_memory"], result.get("memory_updates", []))
                # 更新 tag_candidates
                update_tag_candidates(memory, result.get("tags", []))
                # 标记为已处理（逐篇 checkpoint）
                memory["meta"]["processed_notes"].append(note["name"])
                memory["meta"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
                memory["meta"]["version"] += 1
                memory["meta"]["active_memory_token_estimate"] = token_estimate(
                    json.dumps(memory["active_memory"], ensure_ascii=False), token_method
                )

                # 每篇处理完立即持久化 memory（断点恢复的关键）
                safe_write_json(str(memory_path), memory)
                logger.info(f"✓ 已处理 {note['name']} → {result['category']}")

            # 检查是否需要压缩记忆
            threshold = config.get("memory", {}).get("active_memory_token_threshold", 1500)
            if memory["meta"]["active_memory_token_estimate"] > threshold:
                logger.info("记忆 token 超过阈值，触发压缩...")
                compress_memory(memory, llm, config)
                safe_write_json(str(memory_path), memory)

        except Exception as e:
            logger.error(f"处理笔记组失败 {[n['name'] for n in group]}：{e}")
            # 已持久化的部分不受影响，跳过此组继续下一组
            continue
```

### 5.5 apply_memory_updates()

```python
def apply_memory_updates(active_memory: dict, updates: list) -> dict:
    for update in updates:
        match update["action"]:
            case "APPEND_TO":
                target = get_nested(active_memory, update["path"])
                if isinstance(target, list):
                    if not is_semantically_duplicate(update["value"], target):
                        target.append(update["value"])
            case "SET_IF_NEW":
                if not exists_nested(active_memory, update["path"]):
                    set_nested(active_memory, update["path"], update["value"])
            case _:
                pass  # DELETE / OVERWRITE 直接忽略
    return active_memory
```

---

## 6. 记忆系统

### compress_memory()

```python
def compress_memory(memory: dict, llm, config: dict):
    active_memory = memory["active_memory"]
    history_archive = memory["history_archive"]
    processed_notes = memory["meta"]["processed_notes"]

    # Step 1：将当前 active_memory 完整归档（永久保留）
    history_archive.append({
        "archived_at": today(),
        "trigger": "compression",
        "note_count_at_time": len(processed_notes),
        "snapshot": deepcopy(active_memory)
    })

    # Step 2：调用 LLM 压缩（精简表达，不丢信号）
    system = build_system_prompt("compress_memory", COMPRESSOR_ROLE, config)
    compressed = llm.chat_json(
        system=system,
        user=f"压缩以下记忆，保留所有独特信号：\n{json.dumps(active_memory, ensure_ascii=False)}"
    )

    # Step 3：校验压缩结果结构，防止 LLM 返回格式错误
    if not isinstance(compressed, dict) or not compressed:
        logger.error("压缩结果格式异常，保留原始 active_memory")
        return

    # Step 4：热层瘦身（token 重新降回 ~600）
    memory["active_memory"] = compressed
    token_method = config.get("token_estimation", "char_ratio")
    memory["meta"]["active_memory_token_estimate"] = token_estimate(
        json.dumps(compressed, ensure_ascii=False), token_method
    )
```

### 周快照生成（跨周检测）

```python
def maybe_generate_weekly_snapshot(memory: dict, vault_path: Path):
    """
    检测是否跨越了一个自然周，是则生成快照。
    不依赖“周末执行”，而是比较上次运行日期与当前日期的周数。
    """
    last_updated = memory["meta"].get("last_updated")
    today = datetime.now()
    today_week = today.isocalendar()[1]
    today_year = today.isocalendar()[0]

    if last_updated:
        last_date = datetime.strptime(last_updated, "%Y-%m-%d")
        last_week = last_date.isocalendar()[1]
        last_year = last_date.isocalendar()[0]
        if last_year == today_year and last_week == today_week:
            return  # 同一周，不生成

    # 生成快照
    week_label = f"{today_year}-W{today_week:02d}"
    snapshot = {
        "week": week_label,
        "generated_at": today.strftime("%Y-%m-%d"),
        "note_count": len(memory["meta"]["processed_notes"]),
        "active_memory_snapshot": deepcopy(memory["active_memory"])
    }
    snapshot_path = vault_path / "analysis" / "snapshots" / f"{week_label}.json"
    safe_write_json(str(snapshot_path), snapshot)
    logger.info(f"已生成周快照：{week_label}")
```

---

## 7. 用户形象系统

### assess_change_magnitude()

```python
def assess_change_magnitude(memory_delta: dict) -> str:
    """根据本次 memory_updates 的内容判断变化量级"""
    transformation_signals = ["换城市", "换工作", "重大关系变化", "user_reset"]
    if any(s in str(memory_delta) for s in transformation_signals):
        return "transformation"

    macro_fields = ["ongoing_projects", "current_routines", "interests_observed"]
    if any(field in memory_delta for field in macro_fields):
        return "macro"

    return "micro"
```

### evolve_avatar()

```python
def evolve_avatar(current_avatar: dict, memory_delta: dict, llm, config: dict) -> dict:
    """
    Evolution Mode：根据新笔记带来的记忆变化，对现有形象做增量更新。
    Genesis Mode：直接调用 generate_avatar()。
    """
    magnitude = assess_change_magnitude(memory_delta)

    system = build_system_prompt("generate_avatar_data", ANALYZER_ROLE, config)
    evolution_prompt = f"""
当前形象状态：
{json.dumps(current_avatar['work_me'], ensure_ascii=False)}

本次新笔记带来的记忆变化：
{json.dumps(memory_delta, ensure_ascii=False)}

请对现有形象做增量调整，遵守以下规则：
- core_traits / visual_anchors 是稳定锚点，不轻易修改
- mood / thought_bubble / recent_highlights 可以每次更新
- 新增 room_objects 必须与已有物品协调，优先追加而非替换
- 只有出现明显生活转变的信号，才修改 scene / color_palette
- 返回 JSON，只包含需要变动的字段（增量格式，而非完整替换）
    """

    delta = llm.chat_json(system=system, user=evolution_prompt)
    evolved = apply_avatar_delta(current_avatar, delta)

    evolved["evolution_log"].append({
        "timestamp": today(),
        "change_magnitude": magnitude,
        "trigger_notes": memory_delta.get("source_notes", []),
        "changes_summary": delta
    })

    if config["avatar"]["renderer"] == "pixel_art":
        denoising = {"micro": 0.20, "macro": 0.45, "transformation": 0.80}[magnitude]
        evolved = regenerate_pixel_art(
            evolved,
            denoising=denoising,
            base_seed=current_avatar["avatar_identity"]["base_image_seed"],
            config=config
        )

    return evolved
```

### 7.1 analyze.py — 前端配置导出

Dashboard 前端（纯静态 JS）无法直接读取 Python 的 `config.yml`。`analyze.py` 在生成 dashboard 数据时，同时导出前端需要的配置子集。

```python
# scripts/analyze.py（部分）

def export_frontend_config(config: dict, dashboard_data_dir: Path):
    """将前端需要的配置导出为 JSON，供 app.js 加载"""
    frontend_config = {
        "avatar": {
            "renderer": config.get("avatar", {}).get("renderer", "text_card"),
            "work_scene": config.get("avatar", {}).get("work_scene", "studio"),
            "home_scene": config.get("avatar", {}).get("home_scene", "home"),
        },
        "dashboard_port": config.get("dashboard_port", 8080),
    }
    safe_write_json(str(dashboard_data_dir / "config.json"), frontend_config)


def generate_dashboard_data(config: dict, dry_run: bool = False):
    vault = Path(config["notes_vault_path"]).expanduser()
    dashboard_data_dir = Path("dashboard/data")

    if dry_run:
        logger.info("[DRY-RUN] 将生成 dashboard 数据")
        return

    # ... 生成 stats.json, summaries.json, roadmap.json, profile.json, avatar_data.json ...

    # 导出前端配置
    export_frontend_config(config, dashboard_data_dir)

    # 周快照：检测跨周时自动生成（不依赖"周末执行"）
    memory_path = vault / "analysis" / "memory.json"
    if memory_path.exists():
        memory = json.loads(memory_path.read_text())
        maybe_generate_weekly_snapshot(memory, vault)
```

### 7.2 app.js — 加载配置

```javascript
// app.js
async function init() {
  const config = await fetch("data/config.json").then(r => r.json());
  const avatarData = await fetch("data/avatar_data.json").then(r => r.json());
  mountAvatars(config, avatarData);
}
```

---

## 8. Dashboard 前端

### renderers/base_renderer.js

```javascript
class BaseAvatarRenderer {
  constructor(avatarData, container) {
    this.data = avatarData;
    this.container = container;
  }

  render() {
    throw new Error("子类必须实现 render()");
  }

  destroy() {
    this.container.innerHTML = "";
  }

  // HTML 转义：防止 LLM 生成内容中的 XSS
  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  // 将 energy / stress 映射到预设状态
  getMoodState(energy, stress) {
    if (stress > 0.7)  return "overwhelmed";
    if (energy > 0.7)  return "energized";
    if (energy < 0.3)  return "tired";
    return "focused";
  }
}
```

### renderers/text_card_renderer.js（Phase 1 MVP）

```javascript
class TextCardRenderer extends BaseAvatarRenderer {
  render() {
    const mood = this.getMoodState(
      this.data.core.energy_level,
      this.data.core.stress_level
    );
    const esc = (t) => this.escapeHtml(t);
    this.container.innerHTML = `
      <div class="avatar-card">
        <div class="avatar-placeholder mood-${esc(mood)}"></div>
        <p class="avatar-description">${esc(this.data.description)}</p>
        <div class="avatar-tags">
          ${this.data.traits.map(t => `<span class="tag">${esc(t)}</span>`).join("")}
        </div>
        <ul class="avatar-highlights">
          ${this.data.recent_highlights.map(h => `<li>${esc(h)}</li>`).join("")}
        </ul>
      </div>
    `;
  }
}
```

### renderers/pixel_art_renderer.js（Phase 2）

```javascript
class PixelArtRenderer extends BaseAvatarRenderer {
  async render() {
    // genesis=true → 全新生成；genesis=false → 在 base_image_seed 基础上重绘
    const imgUrl = this.data.generated_image_url;
    const magnitude = this.data._last_change_magnitude || "micro";

    const transitionClass = {
      micro:          "transition-subtle",   // 淡入淡出
      macro:          "transition-morph",    // 溶解过渡
      transformation: "transition-dramatic"  // 强调性切换
    }[magnitude];

    const esc = (t) => this.escapeHtml(t);
    this.container.innerHTML = `
      <div class="avatar-card pixel-style">
        <img src="${esc(imgUrl)}" class="pixel-avatar ${esc(transitionClass)}" alt="avatar" />
        <p class="avatar-description">${esc(this.data.description)}</p>
        <div class="avatar-tags">
          ${this.data.traits.map(t => `<span class="tag">${esc(t)}</span>`).join("")}
        </div>
      </div>
    `;
  }
}
```

### renderers/game_renderer.js（Phase 3 骨架）

```javascript
class GameRenderer extends BaseAvatarRenderer {
  render() {
    const scene = new GameScene({
      character_mood:  this.data.core.mood,
      activity:        this.data.core.primary_activity,
      room_objects:    this.data.room_objects,
      thought:         this.data.thought_bubble,
      palette:         this.data.color_palette
    });
    scene.mount(this.container);
  }
}
```

### app.js — 渲染器加载

```javascript
const RENDERERS = {
  "text_card":        TextCardRenderer,
  "pixel_art":        PixelArtRenderer,
  "animated_sprite":  AnimatedSpriteRenderer,
  "game":             GameRenderer,
};

async function mountAvatars(config, avatarData) {
  const RendererClass = RENDERERS[config.avatar.renderer];

  const workRenderer = new RendererClass(
    avatarData.work_me,
    document.getElementById("work-me-container")
  );
  workRenderer.render();

  const homeRenderer = new RendererClass(
    avatarData.home_me,
    document.getElementById("home-me-container")
  );
  homeRenderer.render();
}
```

---

## 9. 数据结构参考

### memory.json

```json
{
  "meta": {
    "version": 47,
    "last_updated": "2026-06-15",
    "processed_notes": ["2026-06-01.md", "2026-06-14.md", "2026-06-15.md"],
    "active_memory_token_estimate": 620
  },
  "active_memory": {
    "work": {
      "current_focus": "登录模块重构，卡在权限设计上",
      "ongoing_projects": ["认证系统", "dashboard迁移"],
      "recurring_signals": ["容易在细节上花过多时间", "喜欢在写代码前先理清思路"],
      "recent_mood_trend": "疲惫但有动力，本周略有改善"
    },
    "life": {
      "current_routines": ["早上健身", "周末做饭"],
      "recurring_signals": ["睡眠不规律是持续困扰"],
      "interests_observed": ["电影", "编程", "烹饪"]
    },
    "personality_signals": [
      "偏内向，独处时恢复能量",
      "目标感强，对自身完美主义有自我觉察",
      "表达方式直接，情绪起伏不大"
    ]
  },
  "tag_candidates": {
    "backend":      { "count": 5, "status": "active" },
    "sprint":       { "count": 3, "status": "active" },
    "side-project": { "count": 2, "status": "pending" }
  },
  "history_archive": [
    {
      "archived_at": "2026-06-07",
      "trigger": "compression",
      "note_count_at_time": 31,
      "snapshot": {
        "work": { "current_focus": "...", "ongoing_projects": ["..."] },
        "life": {},
        "personality_signals": []
      }
    }
  ]
}
```

### avatar_data.json

```json
{
  "generated_at": "2026-06-15",
  "genesis": false,
  "avatar_identity": {
    "version": 4,
    "established_at": "2026-06-01",
    "last_evolved_at": "2026-06-15",
    "base_image_seed": "deepseek_seed_20260601_7a3f",
    "core_traits": ["注重细节", "内向", "逻辑导向"],
    "visual_anchors": ["眼镜", "深色系穿搭", "短发"],
    "style_era": {
      "name": "early_builder",
      "started_at": "2026-06-01",
      "description": "初期摸索阶段，专注于构建基础，对细节有执着"
    }
  },
  "evolution_log": [
    {
      "timestamp": "2026-06-15",
      "change_magnitude": "micro",
      "trigger_notes": ["2026-06-15.md"],
      "changes_summary": {
        "work_me.core.mood": "focused → tired",
        "work_me.thought_bubble": "这个边界条件到底该怎么处理..."
      }
    }
  ],
  "work_me": {
    "core": { "mood": "focused", "energy_level": 0.7, "stress_level": 0.4, "primary_activity": "deep work" },
    "traits": ["注重细节", "容易过度思考", "逻辑导向"],
    "scene": "studio",
    "description": "工作中的你像一个在迷雾中摸索路径的建筑师...",
    "recent_highlights": ["正在攻克一个复杂的权限设计问题", "本周 code review 效率有所提升"],
    "thought_bubble": "这个边界条件到底该怎么处理...",
    "room_objects": ["机械键盘", "多个显示器", "咖啡杯", "白板"],
    "color_palette": ["#1a1a2e", "#16213e", "#a78bfa"]
  },
  "home_me": {
    "core": { "mood": "relaxed", "energy_level": 0.45, "stress_level": 0.2, "primary_activity": "cooking" },
    "traits": ["享受独处", "有创造力", "喜欢动手"],
    "scene": "home",
    "description": "下班后的你像一个终于可以放松的手艺人...",
    "recent_highlights": ["上周末尝试了新菜谱", "恢复了早起健身的习惯"],
    "thought_bubble": "今晚做什么吃...",
    "room_objects": ["锅铲", "绿植", "书", "瑜伽垫"],
    "color_palette": ["#2d1b00", "#4a3728", "#f59e0b"]
  }
}
```

---

## 10. run.py 实现

```python
import argparse
import webbrowser
from filelock import Timeout
from scripts.process_notes import process_new_notes
from scripts.analyze import generate_dashboard_data
from scripts.serve import start_server
from scripts.utils import load_config, get_process_lock, setup_logging

def main():
    parser = argparse.ArgumentParser(description="Mindraft")
    parser.add_argument("--notes-only", action="store_true")
    parser.add_argument("--analyze",    action="store_true")
    parser.add_argument("--serve",      action="store_true")
    parser.add_argument("--dry-run",    action="store_true")
    args = parser.parse_args()

    config = load_config()
    logger = setup_logging(config)

    if args.serve:
        start_server(config)
        return

    # 获取进程锁，防止并发执行
    lock = get_process_lock(config["notes_vault_path"])
    try:
        with lock:
            if args.analyze:
                generate_dashboard_data(config, dry_run=args.dry_run)
                if not args.dry_run:
                    start_server(config)
                return

            if args.notes_only:
                process_new_notes(config, dry_run=args.dry_run)
                return

            # 默认：完整执行
            process_new_notes(config, dry_run=args.dry_run)
            generate_dashboard_data(config, dry_run=args.dry_run)
            if not args.dry_run:
                start_server(config)
                webbrowser.open(f"http://localhost:{config['dashboard_port']}")
    except Timeout:
        logger.error("另一个 Mindraft 实例正在运行，请等待其完成后再试")
        raise SystemExit(1)

if __name__ == "__main__":
    main()
```

---

## 11. UI 样式

### CSS 设计变量

```css
:root {
  --bg-base:        #0a0a0a;   /* 页面背景 */
  --bg-card:        #111111;   /* 卡片背景 */
  --border:         #222222;   /* 边框 */
  --accent:         #a78bfa;   /* 主色（紫） */
  --accent-dim:     #7c3aed;   /* 主色深 */
  --text-primary:   #e5e5e5;   /* 主文字 */
  --text-secondary: #666666;   /* 次要文字 */
  --success:        #4ade80;   /* 有笔记标记 */
}

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&display=swap');
/* font-family: 'Inter', system-ui, sans-serif; */
```
