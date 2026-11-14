"""No research records or model weights needed for publication guardrail tests."""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'audit_public_release.py'
spec = importlib.util.spec_from_file_location('release_audit_under_test', SCRIPT)
audit_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_mod)


def git(where, *args):
    return subprocess.run(['git', *args], cwd=where, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, check=True)


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        git(self.root, 'init', '-q')
        git(self.root, 'config', 'user.email', 'release-test@example.org')
        git(self.root, 'config', 'user.name', 'Release Fixture')
        with patch.object(audit_mod, 'ROOT', self.root):
            self.guard = audit_mod

    def write_stage(self, file, content):
        path = self.root / file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        git(self.root, 'add', '-f', '--', file)

    def scan(self, history=True):
        with patch.object(audit_mod, 'ROOT', self.root):
            return audit_mod.inspect(audit_mod.index_paths(), with_history=history)

    def test_approved_source(self):
        self.write_stage('backend/engine.py', 'def tokenize(s): return s.split()\n')
        self.assertEqual(self.scan(), [])

    def test_private_dataset_blocked(self):
        self.write_stage('data/research/corpus_expanded_PRIVATE.jsonl', '{"abstract": "not public"}\n')
        self.assertTrue(any('private' in e.lower() for e in self.scan()))

    def test_live_env_blocked(self):
        self.write_stage('web/.env.local', 'NO_REAL_CREDENTIAL=placeholder\n')
        self.assertTrue(self.scan())

    def test_secret_pattern_blocked(self):
        self.write_stage('backend/main.py', 'BAD_TEST_TOKEN="ghp_' + 'A' * 40 + '"\n')
        self.assertTrue(any('credential' in e.lower() for e in self.scan()))

    def test_historical_private_path_blocked_even_after_deleted(self):
        self.write_stage('data/research/review_PRIVATE.csv', 'a,b\n')
        git(self.root, 'commit', '-qm', 'accidental private file')
        git(self.root, 'rm', '-q', '--', 'data/research/review_PRIVATE.csv')
        self.write_stage('backend/engine.py', 'def placeholder(): pass\n')
        git(self.root, 'commit', '-qm', 'cleanup')
        self.assertTrue(any('HISTORY' in e for e in self.scan()))


if __name__ == '__main__':
    unittest.main()
