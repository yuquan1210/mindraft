import json
import os
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.process_notes import process_new_notes


class FakeLLM:
    """模拟 LLM，返回符合 PROCESS_NOTE_SCHEMA（拆分结构）的固定结果。"""

    def __init__(self, response: dict):
        self._response = response

    def chat_json(self, system: str, user: str) -> dict:
        return self._response


DEFAULT_FAKE_RESPONSE = {
    "notes": [
        {
            "title": "Productive Friday",
            "domain": "work",
            "subcategory": "daily",
            "tags": ["auth-system", "refactoring"],
            "summary": "Refactored the login module",
            "rewritten_content": "# Productive Friday\n\nToday I refactored the login module.",
        }
    ],
    "questions": [],
    "memory_updates": [
        {"action": "APPEND_TO", "path": "work.ongoing_projects", "value": "Auth system redesign"},
        {"action": "SET_IF_NEW", "path": "work.current_focus", "value": "Login module refactoring"},
    ],
}

MULTI_DOMAIN_FAKE_RESPONSE = {
    "notes": [
        {
            "title": "Sprint Planning Day",
            "domain": "work",
            "subcategory": "planning",
            "tags": ["sprint"],
            "summary": "Planned the next sprint",
            "rewritten_content": "# Sprint Planning Day\n\nPlanned the next sprint.",
        },
        {
            "title": "Evening Run",
            "domain": "wellbeing",
            "subcategory": "exercise",
            "tags": ["running"],
            "summary": "Went for a run after work",
            "rewritten_content": "# Evening Run\n\nWent for a run to unwind from work stress.",
        },
    ],
    "questions": [],
    "memory_updates": [
        {"action": "APPEND_TO", "path": "wellbeing.recovery_activities", "value": "夜跑"},
    ],
}


def _make_config(vault_path: Path) -> dict:
    return {
        "notes_vault_path": str(vault_path),
        "llm_provider": "kimi",
        "llm_model": "moonshot-v1-32k",
        "api_keys": {"kimi": "fake-key"},
        "token_estimation": "char_ratio",
        "skills": {
            "note_style": {"enabled": True},
            "tagging": {"enabled": True},
        },
        "note_filter": {
            "min_meaningful_chars": 20,
            "batch_short_notes": False,
        },
        "subcategory_vocabulary": {
            "work": ["daily", "planning"],
            "wellbeing": ["exercise"],
        },
    }


def _write_raw_note(vault: Path, name: str, content: str):
    raw_dir = vault / "raw_notes"
    raw_dir.mkdir(parents=True, exist_ok=True)
    (raw_dir / name).write_text(content, encoding="utf-8")


def test_process_single_note_writes_ai_note_and_memory():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        config = _make_config(vault)
        _write_raw_note(vault, "2026-07-26.md", "Today I refactored the login module.")

        fake_llm = FakeLLM(DEFAULT_FAKE_RESPONSE)
        with patch("scripts.process_notes.get_llm", return_value=fake_llm):
            process_new_notes(config, dry_run=False)

        ai_note = vault / "ai_notes" / "work" / "daily" / "productive-friday.md"
        assert ai_note.exists(), f"ai_note not found: {ai_note}"

        ai_content = ai_note.read_text(encoding="utf-8")
        assert "---" in ai_content
        assert "source: raw_notes/2026-07-26.md" in ai_content
        assert "# Productive Friday" in ai_content
        # frontmatter：processed_at 为完整时间戳，tags 为 inline array
        assert re.search(r"processed_at: '\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'", ai_content)
        assert "tags: [auth-system, refactoring]" in ai_content

        memory_path = vault / ".mindraft" / "memory.json"
        assert memory_path.exists(), "memory.json not created"
        memory = json.loads(memory_path.read_text(encoding="utf-8"))

        assert "2026-07-26.md" in memory["meta"]["processed_notes"]
        assert memory["meta"]["version"] == 1
        assert memory["meta"]["active_memory_token_estimate"] > 0

        assert "Auth system redesign" in memory["active_memory"]["work"]["ongoing_projects"]
        assert memory["active_memory"]["work"]["current_focus"] == "Login module refactoring"

        assert memory["tag_candidates"]["auth-system"]["count"] == 1
        assert memory["tag_candidates"]["auth-system"]["status"] == "pending"


def test_split_note_writes_multiple_ai_notes():
    """一篇原笔记拆分为多篇小笔记：写入多个分类目录，part 与 source 正确。"""
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        config = _make_config(vault)
        _write_raw_note(
            vault, "2026-07-27.md",
            "Sprint planning in the morning, went for a run after work to unwind.",
        )

        fake_llm = FakeLLM(MULTI_DOMAIN_FAKE_RESPONSE)
        with patch("scripts.process_notes.get_llm", return_value=fake_llm):
            process_new_notes(config, dry_run=False)

        work_note = vault / "ai_notes" / "work" / "planning" / "sprint-planning-day.md"
        run_note = vault / "ai_notes" / "wellbeing" / "exercise" / "evening-run.md"
        assert work_note.exists(), f"ai_note not found: {work_note}"
        assert run_note.exists(), f"ai_note not found: {run_note}"

        work_content = work_note.read_text(encoding="utf-8")
        run_content = run_note.read_text(encoding="utf-8")
        assert "source: raw_notes/2026-07-27.md" in work_content
        assert "source: raw_notes/2026-07-27.md" in run_content
        assert "part: 1/2" in work_content
        assert "part: 2/2" in run_content

        memory = json.loads(
            (vault / ".mindraft" / "memory.json").read_text(encoding="utf-8")
        )
        assert "2026-07-27.md" in memory["meta"]["processed_notes"]
        # memory_updates 属于整篇原笔记
        assert "夜跑" in memory["active_memory"]["wellbeing"]["recovery_activities"]
        # 所有小笔记的 tags 都计入候选
        assert memory["tag_candidates"]["sprint"]["count"] == 1
        assert memory["tag_candidates"]["running"]["count"] == 1


def test_out_of_vocabulary_subcategory_accepted_with_warning(caplog):
    """词表外的 subcategory 应接受（软约束）并记录 warning。"""
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        config = _make_config(vault)
        _write_raw_note(vault, "2026-07-28.md", "Went bouldering with friends today.")

        response = {
            "notes": [
                {
                    "title": "Bouldering Day",
                    "domain": "wellbeing",
                    "subcategory": "climbing",  # 不在词表 wellbeing: [exercise] 中
                    "tags": [],
                    "summary": "Bouldering with friends",
                    "rewritten_content": "# Bouldering Day\n\nWent bouldering with friends.",
                }
            ],
            "questions": [],
            "memory_updates": [],
        }
        fake_llm = FakeLLM(response)
        with patch("scripts.process_notes.get_llm", return_value=fake_llm):
            with caplog.at_level("WARNING", logger="mindraft"):
                process_new_notes(config, dry_run=False)

        ai_note = vault / "ai_notes" / "wellbeing" / "climbing" / "bouldering-day.md"
        assert ai_note.exists(), "词表外 subcategory 的小笔记应正常写入"
        assert any("词表外" in r.message for r in caplog.records)


def test_dry_run_does_not_write_files():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        config = _make_config(vault)
        _write_raw_note(vault, "2026-07-26.md", "Today I refactored the login module.")

        fake_llm = FakeLLM(DEFAULT_FAKE_RESPONSE)
        with patch("scripts.process_notes.get_llm", return_value=fake_llm):
            process_new_notes(config, dry_run=True)

        assert not (vault / "ai_notes").exists()
        assert not (vault / ".mindraft" / "memory.json").exists()


def test_skipped_note_marked_processed():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        config = _make_config(vault)
        _write_raw_note(vault, "short.md", "hi")  # too short

        fake_llm = FakeLLM(DEFAULT_FAKE_RESPONSE)
        with patch("scripts.process_notes.get_llm", return_value=fake_llm):
            process_new_notes(config, dry_run=False)

        memory_path = vault / ".mindraft" / "memory.json"
        memory = json.loads(memory_path.read_text(encoding="utf-8"))
        assert "short.md" in memory["meta"]["processed_notes"]
        assert not (vault / "ai_notes").exists()


def test_failed_note_not_marked_processed_and_retries():
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        config = _make_config(vault)
        _write_raw_note(vault, "good.md", "Today I refactored the login module.")
        _write_raw_note(vault, "bad.md", "This note will fail schema validation.")

        def fake_chat_json(system, user):
            if "good.md" in user:
                return DEFAULT_FAKE_RESPONSE
            return {"title": "Bad", "domain": "invalid", "subcategory": "daily"}

        fake_llm = FakeLLM(DEFAULT_FAKE_RESPONSE)
        fake_llm.chat_json = fake_chat_json

        with patch("scripts.process_notes.get_llm", return_value=fake_llm):
            process_new_notes(config, dry_run=False)

        memory_path = vault / ".mindraft" / "memory.json"
        memory = json.loads(memory_path.read_text(encoding="utf-8"))
        assert "good.md" in memory["meta"]["processed_notes"]
        assert "bad.md" not in memory["meta"]["processed_notes"]


def test_transient_failure_recovers_on_retry():
    """首次调用失败（如 JSON 解析异常），重试成功后笔记应正常处理。"""
    with tempfile.TemporaryDirectory() as tmp:
        vault = Path(tmp)
        config = _make_config(vault)
        _write_raw_note(vault, "flaky.md", "Today I refactored the login module.")

        call_count = {"n": 0}

        def flaky_chat_json(system, user):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise ValueError("Invalid control character at: line 6 column 40")
            return DEFAULT_FAKE_RESPONSE

        fake_llm = FakeLLM(DEFAULT_FAKE_RESPONSE)
        fake_llm.chat_json = flaky_chat_json

        with patch("scripts.process_notes.get_llm", return_value=fake_llm):
            process_new_notes(config, dry_run=False)

        assert call_count["n"] == 2, f"expected 1 retry, got {call_count['n']} calls"
        memory = json.loads((vault / ".mindraft" / "memory.json").read_text(encoding="utf-8"))
        assert "flaky.md" in memory["meta"]["processed_notes"]


if __name__ == "__main__":
    test_process_single_note_writes_ai_note_and_memory()
    test_split_note_writes_multiple_ai_notes()
    # test_out_of_vocabulary_subcategory_accepted_with_warning 依赖 pytest caplog，仅经 pytest 运行
    test_dry_run_does_not_write_files()
    test_skipped_note_marked_processed()
    test_failed_note_not_marked_processed_and_retries()
    test_transient_failure_recovers_on_retry()
    print("\n所有 process_notes 测试通过。")
