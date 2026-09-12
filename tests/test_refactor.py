from copy import deepcopy
import json
import logging
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from filelock import Timeout

import run
from scripts.analyze import generate_dashboard_data
from scripts.memory_state import load_memory
from scripts.process_notes import apply_memory_updates, process_new_notes
from scripts.schemas import MEMORY_UPDATE_SCHEMA, validate_llm_output
from scripts.utils import safe_write_json, _JsonLogFormatter
from tests.test_process_notes import DEFAULT_FAKE_RESPONSE, MULTI_DOMAIN_FAKE_RESPONSE


@pytest.mark.parametrize('update', [
    {'action': 'SET_IF_NEW', 'path': 'work', 'value': 'domain destroyed'},
    {'action': 'SET_IF_NEW', 'path': 'work.current_focus.child', 'value': 'nested overwrite'},
    {'action': 'SET_IF_NEW', 'path': 'work.current_focus', 'value': ['wrong type']},
    {'action': 'APPEND_TO', 'path': 'work.goals', 'value': {'invalid': True}},
    {'action': 'SET_IF_NEW', 'path': '_condensed.work', 'value': 'overwrite'},
])
def test_invalid_memory_updates_rejected_before_mutation(update):
    active = {'work': {'goals': [], 'current_focus': 'existing'}}
    before = deepcopy(active)
    assert not validate_llm_output(update, MEMORY_UPDATE_SCHEMA)[0]
    apply_memory_updates(active, [update])
    assert active == before


def test_contradictory_and_more_specific_observations_survive():
    active = {'work': {'goals': ['I enjoy working alone']}}
    for value in ['I do not enjoy working alone', 'I enjoy working alone on small projects',
                  '  I enjoy working alone  ']:
        apply_memory_updates(active, [{'action': 'APPEND_TO', 'path': 'work.goals', 'value': value}])
    assert len(active['work']['goals']) == 3


@pytest.mark.parametrize('content', ['{broken', '{"meta": {}, "active_memory": []}'])
def test_corrupt_memory_never_overwrites_dashboard(tmp_path, content):
    memory_path = tmp_path / '.mindraft' / 'memory.json'
    memory_path.parent.mkdir()
    memory_path.write_text(content)
    with patch('scripts.analyze.safe_write_json') as write, patch('scripts.analyze.get_llm') as llm:
        with pytest.raises(ValueError, match='保留原文件'):
            generate_dashboard_data({'notes_vault_path': str(tmp_path)})
    write.assert_not_called()
    llm.assert_not_called()
    assert memory_path.read_text() == content


def test_failed_checkpoint_does_not_leak_into_later_note(tmp_path):
    raw = tmp_path / 'raw_notes'
    raw.mkdir()
    for name in ['a.md', 'b.md']:
        (raw / name).write_text('A meaningful note with enough natural language to process.')
    responses = [deepcopy(DEFAULT_FAKE_RESPONSE), deepcopy(MULTI_DOMAIN_FAKE_RESPONSE)]
    fake = Mock()
    fake.chat_json.side_effect = responses
    def fail_first(path, data):
        if data['meta']['processed_notes'] == ['a.md']:
            raise OSError('checkpoint failed')
        safe_write_json(path, data)
    with patch('scripts.process_notes.get_llm', return_value=fake), \
         patch('scripts.process_notes.safe_write_json', side_effect=fail_first):
        memory = process_new_notes({'notes_vault_path': str(tmp_path)})
    assert memory['meta']['processed_notes'] == ['b.md']
    assert memory['active_memory']['work']['ongoing_projects'] == []
    assert 'auth-system' not in memory['tag_candidates']
    assert not list((tmp_path / 'ai_notes').rglob('productive-friday*.md'))
    assert load_memory(tmp_path / '.mindraft' / 'memory.json') == memory


def test_partial_fragment_write_rolls_back(tmp_path):
    from scripts.process_notes import write_ai_notes
    fragments = deepcopy(MULTI_DOMAIN_FAKE_RESPONSE['notes'])
    for fragment in fragments:
        fragment['category'] = f"{fragment['domain']}/{fragment['subcategory']}"
    original_open = Path.open
    def fail_second(path, *args, **kwargs):
        if path.name == 'evening-run.md':
            raise OSError('disk full')
        return original_open(path, *args, **kwargs)
    with patch.object(Path, 'open', fail_second), pytest.raises(OSError):
        write_ai_notes(tmp_path, 'a.md', fragments)
    assert not list(tmp_path.rglob('*.md'))


def test_lock_timeout_prevents_rebuild_and_migration():
    lock = Mock()
    lock.__enter__ = Mock(side_effect=Timeout('test.lock'))
    lock.__exit__ = Mock()
    with patch('sys.argv', ['run.py', '--rebuild']), patch('run.load_config', return_value={}), \
         patch('run.get_process_lock', return_value=lock), patch('scripts.utils.reset_analysis_state') as reset, \
         patch('run.migrate_legacy_analysis_state') as migrate, patch('run.setup_logging') as logs:
        with pytest.raises(SystemExit):
            run.main()
    reset.assert_not_called()
    migrate.assert_not_called()
    logs.assert_not_called()


def test_dashboard_only_does_not_migrate():
    with patch('sys.argv', ['run.py', '--dashboard']), patch('run.load_config', return_value={}), \
         patch('run.setup_logging'), patch('run.migrate_legacy_analysis_state') as migrate, \
         patch('scripts.serve.start_server') as serve:
        run.main()
    migrate.assert_not_called()
    serve.assert_called_once()


def test_json_log_handles_quotes_and_newlines():
    record = logging.LogRecord('test', logging.INFO, '', 1, 'response: "hello"\n下一行', (), None)
    line = _JsonLogFormatter().format(record)
    assert '\n' not in line
    assert json.loads(line)['msg'] == record.getMessage()


def test_note_routes_stay_inside_generated_directories(tmp_path):
    from scripts.serve import make_handler
    vault = tmp_path / 'vault'
    dashboard = tmp_path / 'dashboard'
    dashboard.mkdir()
    note_dir = vault / 'ai_notes' / 'work'
    note_dir.mkdir(parents=True)
    handler = object.__new__(make_handler({'notes_vault_path': str(vault)}, dashboard))
    assert handler.translate_path('/ai_notes/work/example.md') == str(note_dir / 'example.md')
    for route in ['/ai_notes/../../raw_notes/secret.md', '/ai_notes/%2e%2e/raw_notes/secret.md']:
        assert 'secret.md' not in handler.translate_path(route)
    (note_dir / 'escape').symlink_to(tmp_path)
    assert 'secret.md' not in handler.translate_path('/ai_notes/work/escape/secret.md')


def test_legacy_state_can_be_read_without_migration(tmp_path):
    path = tmp_path / 'analysis' / 'memory.json'
    path.parent.mkdir()
    path.write_text(json.dumps({'meta': {'processed_notes': ['old.md']}, 'active_memory': {}}))
    memory = load_memory(tmp_path / '.mindraft' / 'memory.json')
    assert memory['meta']['processed_notes'] == ['old.md']
    assert path.exists()
    assert not (tmp_path / '.mindraft').exists()


def test_http_serves_dashboard_and_generated_note_only(tmp_path):
    from http.server import ThreadingHTTPServer
    from threading import Thread
    from urllib.request import urlopen
    from urllib.error import HTTPError
    from scripts.serve import make_handler

    dashboard = tmp_path / 'dashboard'
    dashboard.mkdir()
    (dashboard / 'index.html').write_text('<h1>Mindraft</h1>')
    vault = tmp_path / 'vault'
    (vault / 'ai_notes').mkdir(parents=True)
    (vault / 'ai_notes' / 'note.md').write_text('generated note')
    (vault / 'raw_notes').mkdir()
    (vault / 'raw_notes' / 'private.md').write_text('private')
    handler = make_handler({'notes_vault_path': str(vault)}, dashboard)
    with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
        thread = Thread(target=server.serve_forever)
        thread.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            with urlopen(base + '/') as response:
                assert b'Mindraft' in response.read()
            with urlopen(base + '/ai_notes/note.md') as response:
                assert response.read() == b'generated note'
            for route in ['/raw_notes/private.md', '/ai_notes/', '/ai_notes/%2e%2e/raw_notes/private.md']:
                with pytest.raises(HTTPError) as error:
                    urlopen(base + route)
                assert error.value.code == 404
        finally:
            server.shutdown()
            thread.join()
