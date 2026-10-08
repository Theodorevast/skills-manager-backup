#!/usr/bin/env python3
"""Behavior tests in fake home directories; never touches live client data."""
import contextlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import subprocess
import unittest
from unittest.mock import patch

import switch_api as mod


class SwitchingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.s = mod.Switcher(self.home)
        self.write('.claude/settings.json', {'env': {'ANTHROPIC_BASE_URL': 'https://old.example', 'ANTHROPIC_AUTH_TOKEN': 'dummy-old', 'ANTHROPIC_DEFAULT_OPUS_MODEL': 'claude-opus-5-5', 'UNCHANGED': 'preserve'}, 'model': 'opus[1m]', 'effortLevel': 'xhigh', 'permissions': {'deny': ['unrelated']}})
        self.write('Library/Application Support/Claude-3p/configLibrary/_meta.json', {'appliedId': 'abc', 'entries': [{'id': 'abc', 'name': 'Default'}]})
        self.write('Library/Application Support/Claude-3p/configLibrary/abc.json', {'inferenceProvider': 'gateway', 'inferenceCredentialKind': 'static', 'inferenceGatewayBaseUrl': 'https://old.example', 'inferenceGatewayApiKey': 'dummy-old', 'modelDiscoveryEnabled': False, 'inferenceModels': [{'name': 'claude-opus-5-5', 'anthropicFamilyTier': 'opus', 'isFamilyDefault': True}], 'other': {'keep': True}})
        self.write('.claude/projects/project/session.jsonl', '{"message":"original transcript"}\n')
        self.write('.claude/history.jsonl', '{"id":"old"}\n')
        self.write('.claude.json', {'projects': {'project': {'lastSessionId': 'session'}}})
        self.write('Library/Application Support/Claude-3p/claude-code-sessions/account/session.json', {'sessionId': 'session'})
        self.write('Library/Application Support/Claude-3p/local-agent-mode-sessions/account/session.json', {'cowork': 'saved'})
        self.write('Library/Application Support/Claude-3p/claude_desktop_config.json', {'deploymentMode': '3p', 'unrelated': True})
        self.write('.zshrc', '# comment\nexport ANTHROPIC_BASE_URL="https://old.example"\nexport ANTHROPIC_AUTH_TOKEN="dummy-old"\nexport OTHER=keep\n')
        self.source = self.write('new.md', 'API_BASE_URL=https://new.example/team\nAPI_KEY=dummy-new-secret\nMODEL=claude-opus-5-5\n')
        self.s.import_md('new', self.source)
        quiet = patch.object(self.s, 'assert_quiet')
        quiet.start(); self.addCleanup(quiet.stop)
        probe = patch.object(self.s, 'probe', return_value={'ok': True})
        probe.start(); self.addCleanup(probe.stop)

    def write(self, rel, value):
        p = self.home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value if isinstance(value, str) else json.dumps(value))
        return p

    def test_switch_preserves_history_identity_preferences_and_archive(self):
        before = self.s.inventory()
        result = self.s.apply('new')
        self.assertEqual(before, self.s.inventory())
        c, d = self.s.active_paths()
        cfg = mod.read_json(c)
        self.assertEqual(cfg['effortLevel'], 'xhigh')
        self.assertEqual(cfg['env']['UNCHANGED'], 'preserve')
        self.assertEqual(cfg['permissions'], {'deny': ['unrelated']})
        self.assertEqual(mod.read_json(d)['other'], {'keep': True})
        self.assertIn('export OTHER=keep', (self.home/'.zshrc').read_text())
        archive = self.s.root / 'backups' / result['backup_id'] / 'history.tar.gz'
        with tarfile.open(archive) as tar:
            data = tar.extractfile('.claude/projects/project/session.jsonl').read()
            self.assertEqual(data, (self.home/'.claude/projects/project/session.jsonl').read_bytes())
        self.assertTrue(self.s.status()['profiles'][0]['cli_matches'])
        self.assertTrue(self.s.status()['profiles'][0]['desktop_matches'])

    def test_failed_probe_changes_nothing(self):
        before = {p: p.read_bytes() for p in self.s.active_paths()}
        self.s.probe.side_effect = mod.Refused('quota exhausted')
        with self.assertRaises(mod.Refused): self.s.apply('new')
        for p, data in before.items(): self.assertEqual(p.read_bytes(), data)
        self.assertFalse((self.s.root/'backups').exists())

    def test_mid_write_failure_restores_configuration(self):
        paths = self.s.active_paths()
        before = {p: p.read_bytes() for p in paths}
        real = mod.atomic
        failed = False
        def fail_once(path, data, mode=0o600):
            nonlocal failed
            if path == paths[1] and not failed:
                failed = True
                raise OSError('simulated disk error')
            return real(path, data, mode)
        with patch.object(mod, 'atomic', side_effect=fail_once):
            with self.assertRaises(OSError): self.s.apply('new')
        for p, data in before.items(): self.assertEqual(p.read_bytes(), data)

    def test_rollback_keeps_newer_conversations(self):
        paths = self.s.active_paths()
        before = {p: p.read_bytes() for p in paths}
        result = self.s.apply('new')
        self.write('.claude/projects/project/new-session.jsonl', 'new conversation\n')
        history = self.s.inventory()
        self.s.rollback(result['backup_id'])
        self.assertEqual(history, self.s.inventory())
        for p, data in before.items(): self.assertEqual(p.read_bytes(), data)

    def test_rollback_refuses_later_config_edits(self):
        result = self.s.apply('new')
        cli, _ = self.s.active_paths()
        c = mod.read_json(cli); c['effortLevel'] = 'medium'; cli.write_bytes(mod.encoded(c))
        with self.assertRaises(mod.Refused): self.s.rollback(result['backup_id'])
        self.assertEqual(mod.read_json(cli)['effortLevel'], 'medium')

    def test_running_client_blocks_before_probe(self):
        self.s.assert_quiet.side_effect = mod.Refused('Claude running')
        with self.assertRaises(mod.Refused): self.s.apply('new')
        self.s.probe.assert_not_called()

    def test_duplicate_fields_and_profile_overwrite_refused(self):
        self.source.write_text('API_BASE_URL=https://new.example/team\nAPI_KEY=one\nAPI_KEY=two\nMODEL=claude-opus-5-5\n')
        with self.assertRaises(mod.Refused): self.s.import_md('duplicate', self.source)
        self.source.write_text('API_BASE_URL=https://new.example/team\nAPI_KEY=rotated\nMODEL=claude-opus-5-5\n')
        with self.assertRaises(mod.Refused): self.s.import_md('new', self.source)

    def test_outputs_and_permissions(self):
        out = json.dumps(self.s.status()) + json.dumps(self.s.import_md('new', self.source))
        self.assertNotIn('dummy-new-secret', out)
        self.assertEqual(self.s.profile_path('new').stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.s.profile_path('new').parent.stat().st_mode & 0o777, 0o700)

    def test_history_changes_during_backup_abort_before_config_write(self):
        original = self.s.inventory
        count = 0
        def changing():
            nonlocal count
            count += 1
            if count == 2: self.write('.claude/projects/project/concurrent.jsonl', 'changed\n')
            return original()
        before = {p: p.read_bytes() for p in self.s.active_paths()}
        with patch.object(self.s, 'inventory', side_effect=changing):
            with self.assertRaises(mod.Refused): self.s.apply('new')
        for p, data in before.items(): self.assertEqual(p.read_bytes(), data)

    def test_complex_shell_assignment_refused(self):
        self.write('.zshrc', 'export ANTHROPIC_AUTH_TOKEN=old; echo preserve-this\n')
        with self.assertRaises(mod.Refused): self.s.changes(self.s.load('new'))

    def test_standalone_snapshot_changes_no_live_data(self):
        before = {p: p.read_bytes() for p in self.s.active_paths()}
        history = self.s.inventory()
        result = self.s.snapshot()
        self.assertFalse(result['configuration_changed'])
        self.assertEqual(history, self.s.inventory())
        for p, data in before.items(): self.assertEqual(p.read_bytes(), data)
        with self.assertRaises(mod.Refused): self.s.rollback(result['backup_id'])

    def test_cli_probe_keeps_key_out_of_arguments_and_removes_temporary_file(self):
        self.write('.local/bin/claude', 'dummy executable')
        seen = []
        def fake_run(command, **kw):
            self.assertNotIn('dummy-new-secret', ' '.join(command))
            path = Path(command[command.index('--settings') + 1])
            seen.append(path)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(mod.read_json(path)['env']['ANTHROPIC_AUTH_TOKEN'], 'dummy-new-secret')
            self.assertEqual(kw['env']['ANTHROPIC_BASE_URL'], 'https://new.example/team')
            self.assertIn('--no-session-persistence', command)
            self.assertIn('--safe-mode', command)
            return subprocess.CompletedProcess(command, 0, '{"is_error":false,"result":"OK"}', '')
        with patch.object(mod.subprocess, 'run', side_effect=fake_run):
            self.assertTrue(mod.Switcher.probe(self.s, 'new')['ok'])
        self.assertFalse(seen[0].exists())

    def test_real_process_guard_detects_native_cli_version_path(self):
        output = '123 /Users/example/.local/share/claude/versions/2.1.999\n'
        with patch.object(mod.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, output, '')):
            with self.assertRaises(mod.Refused): mod.Switcher.assert_quiet(self.s)


if __name__ == '__main__':
    unittest.main(verbosity=2)
