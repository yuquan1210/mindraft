# scripts/analyze.py
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

import yaml

from scripts.llm_factory import get_llm
from scripts.prompts import DASHBOARD_SUMMARY_ROLE
from scripts.schemas import DASHBOARD_SUMMARY_SCHEMA, validate_llm_output
from scripts.utils import safe_write_json, load_config, get_memory_path

logger = logging.getLogger("mindraft")

DOMAINS = ["work", "life", "growth", "wellbeing", "identity"]
FALLBACK_DAILY_INSIGHT = "今日洞察生成失败，请稍后重试。"

DASHBOARD_DATA_DIR = Path(__file__).parent.parent / "dashboard" / "data"


def generate_dashboard_data(config: dict, dry_run: bool = False):
    """
    生成 Dashboard 所需数据并写入 mindraft/dashboard/data/。

    memory 未变化且数据文件齐全时直接跳过（不调 LLM、不重写文件）；
    需要强制重新生成时使用 run.py --rebuild。

    Args:
        config: 加载后的 config.yml 配置。
        dry_run: 为 True 时调用 LLM 但不写入文件。
    """
    vault = Path(config["notes_vault_path"]).expanduser()
    dashboard_data_dir = DASHBOARD_DATA_DIR

    memory = _load_memory(get_memory_path(config))
    ai_notes_dir = vault / "ai_notes"

    memory_hash = _memory_hash(memory)
    if not dry_run and _dashboard_up_to_date(dashboard_data_dir, memory_hash):
        logger.info("memory 未变化，dashboard 数据已是最新，跳过生成（--rebuild 可强制重建）")
        return

    recent_notes = _build_recent_notes(memory, ai_notes_dir)
    stats = _build_stats(memory, ai_notes_dir)

    # 调用 LLM 生成 summaries
    summaries = _generate_summaries(memory, config, dry_run)

    config_json = {
        "dashboard_title": "Mindraft",
        "version": "0.2.0",
        "memory_hash": memory_hash,
        "data_files": {
            "summaries": "data/summaries.json",
            "stats": "data/stats.json",
            "recent_notes": "data/recent_notes.json",
        },
    }

    if dry_run:
        logger.info("[DRY-RUN] analyze 阶段完成，不写入 dashboard 数据文件")
        logger.debug(f"[DRY-RUN] stats={json.dumps(stats, ensure_ascii=False)}")
        logger.debug(f"[DRY-RUN] recent_notes count={len(recent_notes.get('notes', []))}")
        logger.debug(f"[DRY-RUN] summaries fallback={summaries.get('fallback')}")
        return

    dashboard_data_dir.mkdir(parents=True, exist_ok=True)

    safe_write_json(str(dashboard_data_dir / "summaries.json"), summaries)
    safe_write_json(str(dashboard_data_dir / "stats.json"), stats)
    safe_write_json(str(dashboard_data_dir / "recent_notes.json"), recent_notes)
    safe_write_json(str(dashboard_data_dir / "config.json"), config_json)

    logger.info("Dashboard 数据已生成到 %s", dashboard_data_dir)


def _memory_hash(memory: dict) -> str:
    """memory 内容的稳定哈希，用于判断 dashboard 数据是否需要重新生成。"""
    canonical = json.dumps(memory, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _dashboard_up_to_date(dashboard_data_dir: Path, memory_hash: str) -> bool:
    """dashboard/data 已基于当前 memory 生成且数据文件齐全时返回 True。"""
    config_path = dashboard_data_dir / "config.json"
    if not config_path.exists():
        return False
    data_files = ["summaries.json", "stats.json", "recent_notes.json"]
    if any(not (dashboard_data_dir / name).exists() for name in data_files):
        return False
    try:
        existing = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return False
    return existing.get("memory_hash") == memory_hash


def _load_memory(memory_path: Path) -> dict:
    """读取 {notes_vault}/.mindraft/memory.json，不存在则返回空结构。"""
    if not memory_path.exists():
        logger.warning("memory.json 不存在，使用空记忆结构生成 dashboard")
        return {
            "meta": {"processed_notes": []},
            "active_memory": {d: {} for d in DOMAINS},
            "tag_candidates": {},
        }
    try:
        return json.loads(memory_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"读取 memory.json 失败：{e}，使用空记忆结构")
        return {
            "meta": {"processed_notes": []},
            "active_memory": {d: {} for d in DOMAINS},
            "tag_candidates": {},
        }


def _build_recent_notes(memory: dict, ai_notes_dir: Path) -> dict:
    """
    基于 processed_notes 顺序，从 ai_notes/ 中提取最近 10 篇笔记的元数据。
    """
    processed = memory.get("meta", {}).get("processed_notes", [])
    # 建立 source -> ai_note 路径的映射
    source_to_ai_note = {}
    if ai_notes_dir.exists():
        for ai_path in ai_notes_dir.rglob("*.md"):
            try:
                frontmatter = _extract_frontmatter(ai_path.read_text(encoding="utf-8"))
                source = frontmatter.get("source", "")
                if source:
                    source_to_ai_note[source] = ai_path
            except Exception as e:
                logger.warning(f"解析 ai_note 失败 {ai_path}: {e}")

    notes = []
    for raw_name in processed:
        source_key = f"raw_notes/{raw_name}"
        ai_path = source_to_ai_note.get(source_key)
        if not ai_path:
            continue
        try:
            frontmatter = _extract_frontmatter(ai_path.read_text(encoding="utf-8"))
            category = frontmatter.get("category", "").split("/")[0]
            if category not in DOMAINS:
                continue
            stat = ai_path.stat()
            processed_at = datetime.fromtimestamp(stat.st_mtime).isoformat()
            notes.append(
                {
                    "filename": raw_name,
                    "title": frontmatter.get("title", raw_name),
                    "category": category,
                    "slug": ai_path.stem,
                    "path": str(ai_path.relative_to(ai_notes_dir.parent)),
                    "processed_at": processed_at,
                }
            )
        except Exception as e:
            logger.warning(f"构建 recent_notes 条目失败 {ai_path}: {e}")

    # 按 processed_notes 顺序，最后处理的在最前；取 10 篇
    notes = notes[::-1][:10]
    return {"notes": notes}


def _build_stats(memory: dict, ai_notes_dir: Path) -> dict:
    """统计已处理笔记总数和各 category 数量。"""
    processed = memory.get("meta", {}).get("processed_notes", [])
    category_counts = {d: 0 for d in DOMAINS}

    if ai_notes_dir.exists():
        for category_dir in ai_notes_dir.iterdir():
            if not category_dir.is_dir():
                continue
            category = category_dir.name
            if category not in DOMAINS:
                continue
            count = sum(1 for _ in category_dir.rglob("*.md"))
            category_counts[category] = count

    return {
        "generated_at": datetime.now().isoformat(),
        "total_notes": len(processed),
        "category_counts": category_counts,
    }


def _generate_summaries(memory: dict, config: dict, dry_run: bool) -> dict:
    """调用 LLM 生成每日一句和五域摘要。失败时返回 fallback。"""
    active_memory = memory.get("active_memory", {d: {} for d in DOMAINS})
    tag_candidates = memory.get("tag_candidates", {})

    generated_at = datetime.now().isoformat()

    if dry_run:
        logger.info("[DRY-RUN] 将调用 LLM 生成 dashboard summaries")
        # dry-run 仍需真实调用 LLM 以验证 pipeline，但不写入
        try:
            llm = get_llm(config)
            result = _call_summary_llm(active_memory, tag_candidates, llm)
            logger.info(f"[DRY-RUN] LLM 返回 daily_insight: {result.get('daily_insight', '')[:40]}...")
        except Exception as e:
            logger.warning(f"[DRY-RUN] LLM 调用失败：{e}")
        return {
            "generated_at": generated_at,
            "fallback": True,
            "daily_insight": FALLBACK_DAILY_INSIGHT,
            "domain_summaries": {d: "" for d in DOMAINS},
            "tag_candidates": tag_candidates,
        }

    summaries = {
        "generated_at": generated_at,
        "fallback": False,
        "daily_insight": "",
        "domain_summaries": {d: "" for d in DOMAINS},
        "tag_candidates": tag_candidates,
    }

    try:
        llm = get_llm(config)
        result = _call_summary_llm(active_memory, tag_candidates, llm)
        summaries["daily_insight"] = result.get("daily_insight", "")
        summaries["domain_summaries"] = {
            "work": result.get("work_summary", ""),
            "life": result.get("life_summary", ""),
            "growth": result.get("growth_summary", ""),
            "wellbeing": result.get("wellbeing_summary", ""),
            "identity": result.get("identity_summary", ""),
        }
    except Exception as e:
        logger.error(f"生成 dashboard summaries 失败：{e}，使用 fallback")
        summaries["fallback"] = True
        summaries["daily_insight"] = FALLBACK_DAILY_INSIGHT

    return summaries


def _call_summary_llm(active_memory: dict, tag_candidates: dict, llm) -> dict:
    """调用 LLM 生成 dashboard 摘要。"""
    system = DASHBOARD_SUMMARY_ROLE
    user_content = f"""用户的 active_memory：
{json.dumps(active_memory, ensure_ascii=False, indent=2)}

tag_candidates：
{json.dumps(tag_candidates, ensure_ascii=False, indent=2)}

请生成 dashboard summaries。"""
    result = llm.chat_json(system=system, user=user_content)
    is_valid, error = validate_llm_output(result, DASHBOARD_SUMMARY_SCHEMA)
    if not is_valid:
        raise ValueError(error)
    return result


def _extract_frontmatter(content: str) -> dict:
    """提取 markdown 文件 frontmatter。"""
    if not content.startswith("---\n"):
        return {}
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        return {}
    try:
        return yaml.safe_load(parts[1]) or {}
    except Exception:
        return {}


if __name__ == "__main__":
    cfg = load_config()
    generate_dashboard_data(cfg, dry_run=False)
