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

    def assert_cache_adapters(self, branch=BRANCH, base=BASE, tree=TREE):
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
            GITHUB_BASE_REF='main', GITHUB_HEAD_REF=branch)
        with patch.dict(os.environ, env), patch.object(cache.sys, 'platform', 'win32'), patch.object(cache, 'stable'):
            for admission in (FROZEN, 'EXACT_MAIN_ANCESTOR_GENERIC_SOURCE_PR', 'untrusted'):
                with patch.object(cache, 'admit_original_pr', return_value=admission), \
                        patch.object(dynamic, 'admit_original_pr', return_value=admission):
                    if admission == FROZEN:
                        self.assertEqual(cache.event_mode(head), 'pr')
                        dynamic._release_scope(base, tree, head)
                        for bad_base, bad_tree in (('b'*40, tree), (base, 'd'*40)):
                            with self.assertRaises(ValueError):
                                dynamic._release_scope(bad_base, bad_tree, head)
                    else:
                        with self.assertRaises(ValueError):
                            cache.event_mode(head)
                        with self.assertRaises(ValueError):
                            dynamic._release_scope(base, tree, head)

    def test_cache_adapters_cannot_use_generic_admission(self):
        self.assert_cache_adapters()

    def test_existing_jobs_preserved_and_native_invocation_has_no_write_route(self):
        text = (ROOT/WORKFLOW).read_text(encoding='utf-8')
        original, addition = text.split('\n  v40-invocation-qualification:', 1)
        # Preserve the exact frozen V40 job byte-for-byte, subtracting ONLY
        # the uniquely pinned, separately PR1731-scope-qualified V41 step.
        step = '      - name: V41 original-owner locked issue/ledger read-only preflight\n'
        self.assertEqual(original.count(step), 1)
        old, appended = original.split(step, 1)
        self.assertIn("F139_V41_ORIGINAL_HOST_READONLY_CUSTODY=PASS", appended)
        self.assertIn("github.event_name == 'issue_comment'", appended)
        self.assertIn("F139-V9-STATUS ", appended)
        self.assertIn("original_owner_status", appended)
        self.assertNotIn("Stop-ScheduledTask", appended)
        self.assertNotIn("Disable-ScheduledTask", appended)
        self.assertNotIn("Start-ScheduledTask", appended)
        self.assertNotIn("workflow_dispatch", appended)
        self.assertEqual(old[-2:], "\n\n")
        # This insertion consumes the separator newline originally adjacent
        # to the next job. Hash the exact immutable V40 prefix only.
        self.assertEqual(hashlib.sha256(old[:-1].encode()).hexdigest(),
                         '679e152e9be86b7399c75d247b31966f972a8d2196538b5729f8cf459d4ba063')
        native = addition.split('\n  v40-owner-readonly:', 1)[1]
        self.assertIn('needs: v40-invocation-qualification', native)
        self.assertIn('permissions:\n      contents: read\n      issues: read\n      actions: read', native)
        self.assertIn('--preflight-only', native)
        copy_block = native.split('          if($copyMode) {', 1)[1].split('          } else {', 1)[0]
        read_block = native.split('          } else {', 1)[1]
        self.assertIn('--preflight-only --rehearse-copy', copy_block)
        self.assertNotIn('--rehearse-copy', read_block)
        self.assertIn("$copyMode=[string]$event.comment.body -ceq ('F139-V40-QUALIFY-COPY '+$candidate)", native)
        self.assertIn("$copy.production_executable_qualified -ne $false", copy_block)
        self.assertIn("$copy.actual_typed_generator.executable_sha256 -cne $binaryHash", copy_block)
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



COPY_BRANCH = 'engineering/f139-v40-source-bound-copy-qualification-20261109'
COPY_BASE = 'fa1a0477996bf1fb0568290a3692c57ee8b29b91'
COPY_TREE = '0554ee925e18e5d77b321b817e1bd42b11fd18d5'


class V40CopyScopeTests(unittest.TestCase):
    def admit(self, *, changes=None, base=COPY_BASE, owner=True):
        head = 'd'*40
        request = dict(number=1, author_association=('OWNER' if owner else 'CONTRIBUTOR'),
            user=dict(login='spoonman136668-ai'),
            head=dict(sha=head,ref=COPY_BRANCH,repo=dict(full_name=guard.REPO)),
            base=dict(sha=base,ref='main',repo=dict(full_name=guard.REPO)))
        table = {('diff','--no-renames','--name-only',COPY_BASE,head): '\n'.join(
            sorted(guard.FROZEN_SCOPES[COPY_BRANCH][1]) if changes is None else changes)}
        with tempfile.TemporaryDirectory() as tmp:
            event = Path(tmp)/'event.json'
            event.write_text(json.dumps(dict(number=1,pull_request=request)),encoding='utf-8')
            with patch.dict(os.environ,dict(GITHUB_EVENT_NAME='pull_request',GITHUB_EVENT_PATH=str(event),
                    GITHUB_HEAD_REF=COPY_BRANCH,GITHUB_BASE_REF='main')):
                return guard.admit_original_pr(head,lambda *a:table[a])

    def test_copy_scope_is_exact_owner_authored_six_file_engineering_only(self):
        self.assertEqual(self.admit(),FROZEN)
        paths=sorted(guard.FROZEN_SCOPES[COPY_BRANCH][1])
        for changes in (paths[:-1], paths+[paths[0]], paths+['f139/local_controller.py'],
                        paths+['.github/workflows/qualify.yml'], []):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                self.admit(changes=changes)
        with self.assertRaises(ValueError):self.admit(base='f'*40)
        with self.assertRaises(ValueError):self.admit(owner=False)
        self.assertFalse(guard.generic_paths_safe([WORKFLOW]))

    def test_copy_cache_adapters_reject_generic_mode_and_wrong_base(self):
        V40ReadonlyWorkflowScopeTests().assert_cache_adapters(COPY_BRANCH, COPY_BASE, COPY_TREE)

    def test_fresh_build_copy_path_cannot_be_a_live_installer_or_private_upload(self):
        text=(ROOT/WORKFLOW).read_text(encoding='utf-8')
        native=text.split('\n  v40-owner-readonly:',1)[1]
        copy_block=native.split('          if($copyMode) {',1)[1].split('          } else {',1)[0]
        for required in ("'go1.23.12 windows/amd64'",'go build -trimpath -buildvcs=false',
                         "./cmd/f139-genenv-source", "Join-Path $env:RUNNER_TEMP ('f139-v40-candidate-'",
                         '$copy.production_executable_qualified -ne $false',
                         '$report.source_transition_authorized -ne $false',
                         '$report.live_migration_enabled -ne $false',
                         '$copy.actual_typed_generator.executable_sha256 -cne $binaryHash'):
            self.assertIn(required,copy_block)
        for forbidden in ('Stop-ScheduledTask','Disable-ScheduledTask','Enable-ScheduledTask',
                          '--event-id','--backup','Import-Clixml','EncryptedKeyFile'):
            self.assertNotIn(forbidden,native)
        self.assertIn('path: ${{ steps.candidate.outputs.path }}',native)
        self.assertNotIn('path: ${{ github.workspace }}',native)
        self.assertIn("$manifest | ConvertTo-Json",native)
        self.assertIn("'V40_POSTREAD_MAIN_OR_POLICY_DRIFT'",native)
        self.assertIn("if: startsWith(github.event.comment.body, 'F139-V40-QUALIFY-COPY ')",native)
        self.assertIn("$scriptLines",text)


if __name__ == '__main__':
    unittest.main()
