from copy import deepcopy
from datetime import datetime
import json
from unittest.mock import Mock, patch

from scripts.memory import (compress_memory, maybe_generate_weekly_snapshot,
                            sync_original_order, DOMAINS)
from scripts.process_notes import create_initial_memory, update_tag_candidates
from scripts.utils import safe_write_json, get_memory_path


def fixture_memory(tmp_path):
    memory = create_initial_memory()
    memory['active_memory']['work']['goals'] = [str(i) + '历史观察' * 100 for i in range(8)]
    memory['active_memory']['life']['current_routines'] = ['最近完整原文']
    memory['meta']['last_updated'] = '2026-08-30'
    config = {'notes_vault_path': str(tmp_path), 'memory': {
        'active_memory_token_threshold': 700, 'original_zone_tokens': 30,
        'condensed_zone_token_budget': 100, 'compression_target_ratio': .8}}
    safe_write_json(get_memory_path(config), memory)
    return memory, config


def test_atomic_compression_preserves_snapshot_and_recent_text(tmp_path):
    memory, config = fixture_memory(tmp_path)
    original = deepcopy(memory['active_memory'])
    llm = Mock()
    llm.chat_json.return_value = {d: '工作探索' if d == 'work' else '' for d in DOMAINS}
    with patch('scripts.memory.safe_write_json', wraps=safe_write_json) as write:
        assert compress_memory(memory, llm, config)
        assert write.call_count == 1
    assert memory['history_archive'][0]['snapshot'] == original
    assert memory['active_memory']['life']['current_routines'] == ['最近完整原文']
    assert memory['meta']['active_memory_token_estimate'] <= 560
    assert json.loads(get_memory_path(config).read_text()) == memory
    assert llm.chat_json.call_count == 1


def test_compression_failure_is_noop_and_retries(tmp_path):
    memory, config = fixture_memory(tmp_path)
    before = deepcopy(memory)
    disk = get_memory_path(config).read_bytes()
    llm = Mock()
    llm.chat_json.return_value = {'invalid': True}
    assert not compress_memory(memory, llm, config)
    assert llm.chat_json.call_count == 2
    assert memory == before
    assert get_memory_path(config).read_bytes() == disk


def test_condensed_budget_second_pass_failure_rolls_back(tmp_path):
    memory, config = fixture_memory(tmp_path)
    before = deepcopy(memory)
    llm = Mock()
    llm.chat_json.side_effect = [{d: '过长' * 200 for d in DOMAINS}, {}, {}]
    assert not compress_memory(memory, llm, config)
    assert memory == before
    assert llm.chat_json.call_count == 3


def test_dry_run_compression_only_changes_in_memory(tmp_path):
    memory, config = fixture_memory(tmp_path)
    disk = get_memory_path(config).read_bytes()
    llm = Mock()
    llm.chat_json.return_value = dict.fromkeys(DOMAINS, '')
    assert compress_memory(memory, llm, config, dry_run=True)
    assert memory['history_archive']
    assert get_memory_path(config).read_bytes() == disk


def test_weekly_snapshot_year_boundary_and_dedup(tmp_path):
    memory, config = fixture_memory(tmp_path)
    memory['meta']['last_updated'] = '2025-12-28'
    active = deepcopy(memory['active_memory'])
    now = datetime(2026, 1, 1)
    assert maybe_generate_weekly_snapshot(memory, config, now=now)
    assert memory['history_archive'][0]['iso_week'] == '2025-W52'
    assert memory['active_memory'] == active
    assert not maybe_generate_weekly_snapshot(memory, config, now=now)
    assert not maybe_generate_weekly_snapshot(memory, config, now=datetime(2026, 1, 4))
    assert maybe_generate_weekly_snapshot(memory, config, now=datetime(2026, 1, 5))


def test_order_tracks_new_observations_across_domains():
    memory = create_initial_memory()
    memory['active_memory']['identity']['values'] = ['older']
    sync_original_order(memory)
    memory['active_memory']['work']['goals'] = ['newest']
    sync_original_order(memory)
    assert memory['original_order'][-1] == ['work', 'goals', 'newest']


def test_tags_count_once_per_source_and_promote():
    memory = create_initial_memory()
    for _ in range(3):
        update_tag_candidates(memory, ['writing', 'writing'])
    assert memory['tag_candidates']['writing'] == {'count': 3, 'status': 'active'}


def test_checkpoint_compresses_and_dry_run_passes_result_to_analysis(tmp_path):
    from scripts.process_notes import process_new_notes
    from scripts.analyze import generate_dashboard_data
    from tests.test_process_notes import DEFAULT_FAKE_RESPONSE
    from tests.test_analyze import FakeLLM
    config = {'notes_vault_path': str(tmp_path), 'memory': {
        'active_memory_token_threshold': 700, 'original_zone_tokens': 30}}
    raw = tmp_path / 'raw_notes'
    raw.mkdir()
    note = raw / 'new.md'
    note.write_text('今天完成项目迭代并反思工作方式，晚上散步让自己恢复精力。')
    response = deepcopy(DEFAULT_FAKE_RESPONSE)
    response['memory_updates'] = [
        {'action': 'APPEND_TO', 'path': 'work.goals', 'value': '过去的大量工作观察' * 300},
        {'action': 'APPEND_TO', 'path': 'life.current_routines', 'value': '最新原文'}]
    llm = Mock()
    llm.chat_json.side_effect = [response, dict.fromkeys(DOMAINS, '')]
    with patch('scripts.process_notes.get_llm', return_value=llm):
        memory = process_new_notes(config, dry_run=True)
    assert llm.chat_json.call_count == 2
    assert memory['history_archive'][0]['trigger'] == 'compression'
    fake = FakeLLM()
    with patch('scripts.analyze.get_llm', return_value=fake), patch('scripts.analyze.DASHBOARD_DATA_DIR', tmp_path / 'data'):
        generate_dashboard_data(config, dry_run=True, memory=memory)
    assert fake.call_count == 1
    assert list(tmp_path.iterdir()) == [raw]
    assert note.read_text() == '今天完成项目迭代并反思工作方式，晚上散步让自己恢复精力。'


def test_atomic_write_failure_keeps_in_memory_state(tmp_path):
    memory, config = fixture_memory(tmp_path)
    original = deepcopy(memory)
    llm = Mock()
    llm.chat_json.return_value = dict.fromkeys(DOMAINS, '')
    with patch('scripts.memory.safe_write_json', side_effect=OSError('disk full')):
        assert not compress_memory(memory, llm, config)
    assert memory == original
