import os
import runpy
import sys


def _make_mock_svc(recorder, rows=None):
    rows = rows or []

    class MockTable:
        def __init__(self, name):
            self.name = name

        def insert(self, payload):
            recorder['inserted'] = payload
            return self

        def select(self, *args, **kwargs):
            recorder['select_called'] = True
            return self

        def order(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def execute(self):
            class R:
                data = rows

            return R()

    class MockSvc:
        def table(self, name):
            recorder.setdefault('tables', []).append(name)
            return MockTable(name)

    return MockSvc()


def test_apply_inserts(monkeypatch, tmp_path):
    # Ensure env vars are present
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE', 'service-role-key')

    recorder = {}

    # Patch the service factory before executing the script
    monkeypatch.setattr('utils.session.get_supabase_service', lambda: _make_mock_svc(recorder), raising=True)

    # Simulate CLI args for --apply
    monkeypatch.setattr(sys, 'argv', ['example_admin_actions.py', '--apply'])

    # Run the script; it will execute main() because run_name='__main__'
    runpy.run_path('scripts/example_admin_actions.py', run_name='__main__')

    assert 'inserted' in recorder, 'Expected script to insert an admin_actions row when --apply is passed'


def test_fetch_recent_actions(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE', 'service-role-key')

    sample_rows = [{'id': 1, 'action': 'example', 'admin_email': 'a@b.c'}]
    recorder = {}

    monkeypatch.setattr('utils.session.get_supabase_service', lambda: _make_mock_svc(recorder, rows=sample_rows), raising=True)
    monkeypatch.setattr(sys, 'argv', ['example_admin_actions.py'])

    # Running the script should fetch and print recent actions; no exception means success
    runpy.run_path('scripts/example_admin_actions.py', run_name='__main__')

    assert recorder.get('tables') and 'admin_actions' in recorder.get('tables'), 'Expected script to query admin_actions table'
