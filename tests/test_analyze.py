import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.analyze import generate_dashboard_data, _memory_hash


class FakeLLM:
    """模拟 LLM，返回符合 DASHBOARD_SUMMARY_SCHEMA 的固定结果，并记录调用次数。"""

    def __init__(self):
        self.call_count = 0

    def chat_json(self, system: str, user: str) -> dict:
        self.call_count += 1
        return {
            "daily_insight": "测试洞察",
            "mbti_description": "你善于观察自己的状态。",
            "work_summary": "w",
            "life_summary": "l",
            "growth_summary": "g",
            "wellbeing_summary": "we",
            "identity_summary": "i",
        }


def _make_vault(vault_path: Path, memory: dict | None = None) -> dict:
    """创建临时 vault，写入 memory.json，返回 config。"""
    (vault_path / ".mindraft").mkdir(parents=True)
    if memory is None:
        memory = {
            "meta": {"processed_notes": ["note-a.md"]},
            "active_memory": {d: {} for d in ["work", "life", "growth", "wellbeing", "identity"]},
            "tag_candidates": {},
        }
    (vault_path / ".mindraft" / "memory.json").write_text(
        json.dumps(memory, ensure_ascii=False), encoding="utf-8"
    )
    return {"notes_vault_path": str(vault_path)}


def _run_with_fake_llm(config, data_dir):
    fake = FakeLLM()
    with patch("scripts.analyze.DASHBOARD_DATA_DIR", data_dir), \
         patch("scripts.analyze.get_llm", return_value=fake):
        generate_dashboard_data(config, dry_run=False)
    return fake


def test_skips_regeneration_when_memory_unchanged(tmp_path):
    config = _make_vault(tmp_path / "vault")
    data_dir = tmp_path / "dashboard" / "data"

    fake = _run_with_fake_llm(config, data_dir)
    assert fake.call_count == 1

    # memory 未变：第二次跳过，不再调用 LLM
    fake = _run_with_fake_llm(config, data_dir)
    assert fake.call_count == 0


def test_regenerates_when_memory_changed(tmp_path):
    config = _make_vault(tmp_path / "vault")
    data_dir = tmp_path / "dashboard" / "data"

    _run_with_fake_llm(config, data_dir)

    memory = json.loads(
        (tmp_path / "vault" / ".mindraft" / "memory.json").read_text(encoding="utf-8")
    )
    memory["active_memory"]["work"] = {"goals": ["新目标"]}
    (tmp_path / "vault" / ".mindraft" / "memory.json").write_text(
        json.dumps(memory, ensure_ascii=False), encoding="utf-8"
    )

    fake = _run_with_fake_llm(config, data_dir)
    assert fake.call_count == 1


def test_regenerates_when_data_file_missing(tmp_path):
    config = _make_vault(tmp_path / "vault")
    data_dir = tmp_path / "dashboard" / "data"

    _run_with_fake_llm(config, data_dir)
    (data_dir / "summaries.json").unlink()

    fake = _run_with_fake_llm(config, data_dir)
    assert fake.call_count == 1


def test_recent_notes_includes_all_fragments_of_one_source(tmp_path):
    """一篇原笔记拆分为多篇 ai_note 时，recent_notes 不应丢条目。"""
    vault = tmp_path / "vault"
    memory = {
        "meta": {"processed_notes": ["note-a.md"]},
        "active_memory": {d: {} for d in ["work", "life", "growth", "wellbeing", "identity"]},
        "tag_candidates": {},
    }
    config = _make_vault(vault, memory)

    def _write_ai_note(category: str, slug: str, part: str):
        note_dir = vault / "ai_notes" / category
        note_dir.mkdir(parents=True, exist_ok=True)
        (note_dir / f"{slug}.md").write_text(
            f"""---
title: {slug}
category: {category}
tags: []
summary: s
source: raw_notes/note-a.md
part: {part}
---

body
""",
            encoding="utf-8",
        )

    _write_ai_note("work/planning", "sprint-planning-day", "1/2")
    _write_ai_note("wellbeing/exercise", "evening-run", "2/2")

    data_dir = tmp_path / "dashboard" / "data"
    _run_with_fake_llm(config, data_dir)

    recent = json.loads((data_dir / "recent_notes.json").read_text(encoding="utf-8"))
    titles = [n["title"] for n in recent["notes"]]
    assert "sprint-planning-day" in titles
    assert "evening-run" in titles


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_skips_regeneration_when_memory_unchanged(tmp_path / "t1")
        test_regenerates_when_memory_changed(tmp_path / "t2")
        test_regenerates_when_data_file_missing(tmp_path / "t3")
        test_recent_notes_includes_all_fragments_of_one_source(tmp_path / "t4")
    print("All tests passed!")


def test_archive_and_tags_refresh_without_llm(tmp_path):
    config = _make_vault(tmp_path / "vault")
    data_dir = tmp_path / "data"
    _run_with_fake_llm(config, data_dir)
    path = tmp_path / "vault" / ".mindraft" / "memory.json"
    memory = json.loads(path.read_text())
    memory["history_archive"] = [{"archived_at": "2026-01-01", "snapshot": memory["active_memory"]}]
    memory["tag_candidates"] = {"writing": {"count": 3, "status": "active"}}
    path.write_text(json.dumps(memory))
    assert _run_with_fake_llm(config, data_dir).call_count == 0
    assert len(json.loads((data_dir / "roadmap.json").read_text())["nodes"]) == 1
    assert json.loads((data_dir / "summaries.json").read_text())["tag_candidates"] == memory["tag_candidates"]


def test_missing_profile_forces_generation(tmp_path):
    config = _make_vault(tmp_path / "vault")
    data_dir = tmp_path / "data"
    _run_with_fake_llm(config, data_dir)
    (data_dir / "profile.json").unlink()
    assert _run_with_fake_llm(config, data_dir).call_count == 1


def test_summary_schema_retry_and_fallback_not_cached(tmp_path):
    from unittest.mock import Mock
    config = _make_vault(tmp_path / "vault")
    data_dir = tmp_path / "data"
    fake = Mock()
    fake.chat_json.return_value = {}
    with patch("scripts.analyze.DASHBOARD_DATA_DIR", data_dir), patch("scripts.analyze.get_llm", return_value=fake):
        generate_dashboard_data(config)
    assert fake.chat_json.call_count == 2
    assert json.loads((data_dir / "profile.json").read_text())["fallback"]
    assert _run_with_fake_llm(config, data_dir).call_count == 1


def test_analyze_dry_run_does_not_write(tmp_path):
    config = _make_vault(tmp_path / "vault")
    path = tmp_path / "vault" / ".mindraft" / "memory.json"
    memory = json.loads(path.read_text())
    memory["meta"]["last_updated"] = "2020-01-01"
    path.write_text(json.dumps(memory))
    before = path.read_bytes()
    data_dir = tmp_path / "data"
    fake = FakeLLM()
    with patch("scripts.analyze.DASHBOARD_DATA_DIR", data_dir), patch("scripts.analyze.get_llm", return_value=fake):
        generate_dashboard_data(config, dry_run=True)
    assert fake.call_count == 1
    assert path.read_bytes() == before
    assert not data_dir.exists()


def test_partial_dashboard_publication_invalidates_cache(tmp_path):
    config = _make_vault(tmp_path / 'vault')
    data_dir = tmp_path / 'data'
    _run_with_fake_llm(config, data_dir)
    profile_path = data_dir / 'profile.json'
    profile = json.loads(profile_path.read_text())
    profile['memory_hash'] = 'different-generation'
    profile_path.write_text(json.dumps(profile))
    assert _run_with_fake_llm(config, data_dir).call_count == 1
