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
            "work_summary": "w",
            "life_summary": "l",
            "growth_summary": "g",
            "wellbeing_summary": "we",
            "identity_summary": "i",
        }


def _make_vault(vault_path: Path, memory: dict | None = None) -> dict:
    """创建临时 vault，写入 memory.json，返回 config。"""
    (vault_path / "analysis").mkdir(parents=True)
    if memory is None:
        memory = {
            "meta": {"processed_notes": ["note-a.md"]},
            "active_memory": {d: {} for d in ["work", "life", "growth", "wellbeing", "identity"]},
            "tag_candidates": {},
        }
    (vault_path / "analysis" / "memory.json").write_text(
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
        (tmp_path / "vault" / "analysis" / "memory.json").read_text(encoding="utf-8")
    )
    memory["tag_candidates"] = {"new-tag": 1}
    (tmp_path / "vault" / "analysis" / "memory.json").write_text(
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


if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        test_skips_regeneration_when_memory_unchanged(tmp_path / "t1")
        test_regenerates_when_memory_changed(tmp_path / "t2")
        test_regenerates_when_data_file_missing(tmp_path / "t3")
    print("All tests passed!")
