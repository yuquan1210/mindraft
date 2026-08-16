import json
import logging
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import yaml
from filelock import FileLock

logger = logging.getLogger("mindraft")


# ── 配置加载 ──────────────────────────────────────────
def _resolve_env_placeholders(value):
    """递归解析字符串中的 ${ENV_VAR} 环境变量占位符。未设置的环境变量保留原样。"""
    if isinstance(value, str):
        pattern = re.compile(r"\$\{([^}]+)\}")

        def replacer(match):
            env_var = match.group(1)
            env_value = os.environ.get(env_var)
            if env_value is None:
                # 不强制所有占位符必须设置，未设置时保留原样
                return match.group(0)
            return env_value

        return pattern.sub(replacer, value)
    if isinstance(value, dict):
        return {k: _resolve_env_placeholders(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_placeholders(item) for item in value]
    return value


def load_config(path: str = "config.yml") -> dict:
    """加载 config.yml，解析环境变量占位符，并展开 notes_vault_path 中的 ~。"""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path.absolute()}")

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config = _resolve_env_placeholders(config)

    vault_path = config.get("notes_vault_path")
    if vault_path:
        config["notes_vault_path"] = str(Path(vault_path).expanduser())

    return config


# ── Token 估算 ──────────────────────────────────────────
def token_estimate(text: str, method: str = "char_ratio") -> int:
    """
    估算文本 token 数。
    - char_ratio：中文按 字符数/1.5 估算，英文按 字符数/4 估算，混合取加权平均
    - tiktoken：使用 tiktoken 库精确计算（需安装 tiktoken）
    """
    if method == "tiktoken":
        try:
            import tiktoken
        except ImportError as e:
            raise ImportError(
                "tiktoken 模式需要安装 tiktoken 包。运行: pip install tiktoken"
            ) from e
        enc = tiktoken.encoding_for_model("gpt-4")
        return len(enc.encode(text))

    # char_ratio 模式：中文字符 ≈ 1.5 token，英文 ≈ 4 chars/token
    chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
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
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, filepath)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


# ── 进程锁 ──────────────────────────────────────────
def get_process_lock(notes_vault_path: str) -> FileLock:
    """获取进程级文件锁，防止并发执行"""
    lock_path = Path(notes_vault_path) / "analysis" / ".mindraft.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    return FileLock(str(lock_path), timeout=10)


# ── 状态重置 ──────────────────────────────────────────
def reset_analysis_state(config: dict) -> list[str]:
    """
    清空全部分析产物（--rebuild 用），返回已删除的路径列表：
    - {vault}/analysis/memory.json
    - {vault}/analysis/process_log.jsonl（按 config.logging.file 定位）
    - {vault}/ai_notes/ 整个目录
    - dashboard/data/*.json
    raw_notes/ 与 .mindraft.lock 不动。
    注意：必须在 setup_logging() 之前调用，否则日志文件句柄已打开，
    删除后新日志会写入已删除的 inode。
    """
    vault = Path(config["notes_vault_path"]).expanduser()
    removed = []

    log_file = vault / config.get("logging", {}).get("file", "analysis/process_log.jsonl")
    for path in [vault / "analysis" / "memory.json", log_file]:
        if path.exists():
            path.unlink()
            removed.append(str(path))

    ai_notes_dir = vault / "ai_notes"
    if ai_notes_dir.exists():
        shutil.rmtree(ai_notes_dir)
        removed.append(str(ai_notes_dir))

    dashboard_data_dir = Path(__file__).parent.parent / "dashboard" / "data"
    if dashboard_data_dir.exists():
        for json_file in dashboard_data_dir.glob("*.json"):
            json_file.unlink()
            removed.append(str(json_file))

    return removed


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

    # 避免重复添加 handler（重复调用 setup_logging 时）
    if logger.handlers:
        logger.handlers.clear()

    # 控制台：简洁格式
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(console)

    # 文件：JSONL 格式，便于程序解析
    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter('{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}')
    )
    logger.addHandler(file_handler)

    return logger


# ── 时间辅助 ──────────────────────────────────────────
def today_iso() -> str:
    """返回当前日期的 ISO 格式字符串（YYYY-MM-DD）。"""
    return datetime.now().strftime("%Y-%m-%d")


# ── 字典点号路径访问 ──────────────────────────────────────────
def get_nested(data: dict, path: str):
    """按点号路径获取字典嵌套值。路径不存在时返回 None。"""
    if not path:
        return data
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]
    return current


def set_nested(data: dict, path: str, value):
    """按点号路径设置字典嵌套值，路径不存在时自动创建中间字典。"""
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def exists_nested(data: dict, path: str) -> bool:
    """按点号路径判断字典嵌套值是否存在。"""
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]
    return True
