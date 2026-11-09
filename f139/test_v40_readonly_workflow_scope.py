"""V40 owner invocation qualification only; never owner access or dispatch."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from scripts import check_rar_g145_pr_scope as guard

BRANCH = 'engineering/f139-v40-qualified-readonly-route-20261109'
BASE = '32de33753c874102de9672d2768e4b7c0b866b25'
TREE = '22d135f137c371c395604315605dbf5cb4f776a2'
WORKFLOW = '.github/workflows/f139-g54-v9-owner-cutover.yml'
FROZEN = 'FROZEN_G141_G144_OR_G145_HARNESS_DEVELOPMENT'
ROOT = Path(__file__).resolve().parents[1]


class V40ReadonlyWorkflowScopeTests(unittest.TestCase):
    def admit(self, *, base=BASE, branch=BRANCH, changes=None, owner=True):
        head = 'c' * 40
        request = dict(number=1, author_association=('OWNER' if owner else 'CONTRIBUTOR'), user=dict(login='spoonman136668-ai'),
            head=dict(sha=head, ref=branch, repo=dict(full_name=guard.REPO)),
            base=dict(sha=base, ref='main', repo=dict(full_name=guard.REPO)))
        reads = {('diff', '--no-renames', '--name-only', BASE, head):
                 '\n'.join(sorted(guard.FROZEN_SCOPES[BRANCH][1]) if changes is None else changes),
                 ('merge-base', base, head): base}
        with tempfile.TemporaryDirectory() as tmp:
            event = Path(tmp) / 'event.json'
            event.write_text(json.dumps(dict(number=1, pull_request=request)), encoding='utf-8')
            with patch.dict(os.environ, dict(GITHUB_EVENT_NAME='pull_request',
                    GITHUB_EVENT_PATH=str(event), GITHUB_HEAD_REF=branch, GITHUB_BASE_REF='main')):
                return guard.admit_original_pr(head, lambda *a: reads[a])

    def test_exact_six_file_frozen_scope_only(self):
        self.assertEqual(self.admit(), FROZEN)
        paths = sorted(guard.FROZEN_SCOPES[BRANCH][1])
        for changes in (paths[:-1], paths+[paths[0]], paths+['f139/local_controller.py'],
                        paths+['.github/workflows/qualify.yml'], [], [WORKFLOW]):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'FROZEN_BRANCH_SCOPE_CHANGED'):
                self.admit(changes=changes)
        with self.assertRaises(ValueError):
            self.admit(base='b'*40)
        with self.assertRaisesRegex(ValueError, 'GENERIC_PR_CHANGED_OR_UNRELATED_HARNESS'):
            self.admit(branch='engineering/unapproved-copy')
        with self.assertRaisesRegex(ValueError, 'ORIGINAL_OWNER_PR_REQUIRED'):
            self.admit(owner=False)
        self.assertFalse(guard.generic_paths_safe([WORKFLOW]))
        guard.negative_controls()

    def test_cache_adapters_cannot_use_generic_admission(self):
        def load(name):
            spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/(name+'.py'))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        with patch.dict(sys.modules, {'check_rar_g145_pr_scope': guard}):
            cache = load('check_rar_g148_go_cache')
            with patch.dict(sys.modules, {'check_rar_g148_go_cache': cache}):
                dynamic = load('check_rar_g156_dynamic_base_cache')
        head = 'c'*40
        env = dict(GITHUB_ACTIONS='true', GITHUB_REPOSITORY=guard.REPO, RUNNER_OS='Windows',
            G148_HEAD=head, RUNNER_TEMP='unused', GITHUB_EVENT_NAME='pull_request',
            GITHUB_BASE_REF='main', GITHUB_HEAD_REF=BRANCH)
        with patch.dict(os.environ, env), patch.object(cache.sys, 'platform', 'win32'), patch.object(cache, 'stable'):
            for admission in (FROZEN, 'EXACT_MAIN_ANCESTOR_GENERIC_SOURCE_PR', 'untrusted'):
                with patch.object(cache, 'admit_original_pr', return_value=admission), \
                        patch.object(dynamic, 'admit_original_pr', return_value=admission):
                    if admission == FROZEN:
                        self.assertEqual(cache.event_mode(head), 'pr')
                        dynamic._release_scope(BASE, TREE, head)
                        for bad_base, bad_tree in (('b'*40, TREE), (BASE, 'd'*40)):
                            with self.assertRaises(ValueError):
                                dynamic._release_scope(bad_base, bad_tree, head)
                    else:
                        with self.assertRaises(ValueError):
                            cache.event_mode(head)
                        with self.assertRaises(ValueError):
                            dynamic._release_scope(BASE, TREE, head)

    def test_existing_jobs_preserved_and_native_invocation_has_no_write_route(self):
        text = (ROOT/WORKFLOW).read_text(encoding='utf-8')
        original, addition = text.split('\n  v40-invocation-qualification:', 1)
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(), '679e152e9be86b7399c75d247b31966f972a8d2196538b5729f8cf459d4ba063')
        native = addition.split('\n  v40-owner-readonly:', 1)[1]
        self.assertIn('needs: v40-invocation-qualification', native)
        self.assertIn('permissions:\n      contents: read\n      issues: read\n      actions: read', native)
        self.assertIn('--preflight-only', native)
        self.assertNotIn('--rehearse-copy', native)
        for forbidden in ('Stop-ScheduledTask', 'Start-ScheduledTask', 'Disable-ScheduledTask',
                          'Enable-ScheduledTask', 'Register-ScheduledTask', 'Stop-Process',
                          'Invoke-Expression', 'EncryptedKeyFile', 'Import-Clixml',
                          'update_ref', '--method', '--event-id'):
            self.assertNotIn(forbidden, native)
        self.assertIn("$env:GITHUB_RUN_ATTEMPT -cne '1'", native)
        self.assertIn("'V40_EXACT_OWNER_READONLY_EVENT_REQUIRED'", native)
        self.assertIn("'V40_EXACT_MAIN_QUALIFICATION_REQUIRED'", native)
        self.assertIn("$sid -cne $identity.User.Value", native)
        self.assertIn("$expectedDb=Join-Path", native)
        self.assertIn("$event.comment.author_association -cne 'OWNER'", native)
        self.assertIn("$null -ne $event.issue.PSObject.Properties['pull_request']", native)

if __name__ == '__main__':
    unittest.main()
