"""Hot memory maintenance; archives and replacement are committed together."""
from copy import deepcopy
from datetime import datetime
import json
import logging

from scripts.prompts import COMPRESSOR_ROLE
from scripts.schemas import COMPRESSION_SCHEMA
from scripts.skill_loader import build_system_prompt
from scripts.utils import safe_write_json, get_memory_path, token_estimate
from scripts.llm_calls import call_with_retry

logger = logging.getLogger("mindraft")
DOMAINS = ("work", "life", "growth", "wellbeing", "identity")


def observations(active):
    return [[domain, key, value] for domain in DOMAINS
            for key, values in active.get(domain, {}).items()
            for value in (values if isinstance(values, list) else [values]) if value]


def sync_original_order(memory):
    """Legacy observations have no timestamps; preserve their stored order."""
    current = observations(memory["active_memory"])
    order = [item for item in memory.get("original_order", []) if item in current]
    order.extend(item for item in current if item not in order)
    memory["original_order"] = order


def iso_week(date):
    year, week, _ = date.isocalendar()
    return f"{year}-W{week:02d}"


def archive_entry(memory, trigger, now, week=None):
    return {"archived_at": now.isoformat(), "iso_week": week or iso_week(now),
            "trigger": trigger,
            "note_count_at_time": len(memory.get("meta", {}).get("processed_notes", [])),
            "tags": deepcopy(memory.get("tag_candidates", {})),
            "snapshot": deepcopy(memory["active_memory"])}


def maybe_generate_weekly_snapshot(memory, config, dry_run=False, now=None):
    now = now or datetime.now()
    meta = memory.get("meta", {})
    last = meta.get("weekly_checkpoint") or meta.get("last_updated")
    if not last:
        return False
    try:
        previous = datetime.fromisoformat(last)
    except ValueError:
        logger.warning("无法解析周快照日期 %s", last)
        return False
    if iso_week(previous) >= iso_week(now):
        return False
    candidate = deepcopy(memory)
    candidate.setdefault("history_archive", []).append(
        archive_entry(memory, "weekly", now, iso_week(previous)))
    candidate["meta"]["weekly_checkpoint"] = now.isoformat()
    if not dry_run:
        safe_write_json(get_memory_path(config), candidate)
    memory.clear()
    memory.update(candidate)
    return True


def compress_memory(memory, llm, config, dry_run=False):
    settings = config.get("memory", {})
    method = config.get("token_estimation", "char_ratio")
    def tokens(value):
        return token_estimate(json.dumps(value, ensure_ascii=False), method)
    threshold = settings.get("active_memory_token_threshold", 1500)
    if tokens(memory["active_memory"]) <= threshold:
        return False
    candidate = deepcopy(memory)
    sync_original_order(candidate)
    order = candidate["original_order"]
    keep = []
    for item in reversed(order):
        if keep and tokens([item] + keep) > settings.get("original_zone_tokens", 300):
            break
        keep.insert(0, item)  # Never split even an oversized newest observation.
    older = order[:len(order) - len(keep)]
    condensed = deepcopy(memory["active_memory"].get("_condensed", {d: "" for d in DOMAINS}))
    budget = settings.get("condensed_zone_token_budget", 900)
    target = int(threshold * settings.get("compression_target_ratio", 0.55))
    system = build_system_prompt("compress_memory", COMPRESSOR_ROLE, config)
    try:
        if older:
            result = call_with_retry(llm, system, json.dumps({
                "observations": older, "target_tokens": max(1, target - tokens(keep) - tokens(condensed))
            }, ensure_ascii=False), COMPRESSION_SCHEMA)
            for domain in DOMAINS:
                condensed[domain] = "\n".join(filter(None, [condensed.get(domain, ""), result[domain]]))
        if tokens(condensed) > budget:
            condensed = call_with_retry(llm, system, json.dumps({
                "condensed": condensed, "target_tokens": max(1, min(budget, target - tokens(keep)))
            }, ensure_ascii=False), COMPRESSION_SCHEMA)
        if not older and condensed == memory["active_memory"].get("_condensed", {d: "" for d in DOMAINS}):
            logger.warning("记忆超阈值，但仅有不可拆分的近期原文，暂不压缩")
            return False
        active = deepcopy(memory["active_memory"])
        for domain in DOMAINS:
            for key, value in active.get(domain, {}).items():
                retained = [item[2] for item in keep if item[:2] == [domain, key]]
                active[domain][key] = retained if isinstance(value, list) else (retained[0] if retained else "")
        active["_condensed"] = condensed
        candidate["active_memory"] = active
        candidate["original_order"] = keep
        candidate.setdefault("history_archive", []).append(archive_entry(memory, "compression", datetime.now()))
        candidate["meta"]["active_memory_token_estimate"] = tokens(active)
        if tokens(active) > target:
            logger.warning("压缩后 %s tokens 仍超过目标 %s；接受本次结果，不循环压缩", tokens(active), target)
        if not dry_run:
            safe_write_json(get_memory_path(config), candidate)
    except Exception as exc:
        logger.error("记忆压缩失败，保留原记忆与归档，下次运行重试：%s", exc)
        return False
    memory.clear()
    memory.update(candidate)
    return True
