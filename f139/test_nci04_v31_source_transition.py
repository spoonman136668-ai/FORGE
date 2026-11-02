"""Maintenance custody mechanics; synthetic fixtures are not live owner proof."""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from f139.local_controller import Database, SingleOwner
from f139 import nci04_v31_source_transition as route

ROOT = Path(__file__).resolve().parent.parent

class MaintenanceTransitionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / 'isolated.sqlite'
        self.db = Database.initialize(self.path, route.FROM_V30)
        self.addCleanup(self.db.close)
        self.db.enable(legacy_suspended=True)
        self.before = self.db.meta().copy()
        self.proof = dict(schema=route.SCHEMA, from_source_sha=route.FROM_V30,
            to_source_sha='f'*40, owner_event_id=41300000000,
            prior_event_head_sha256=self.before['head_hash'],
            verified_historical_tasks=32, custodied_negative_tasks=17,
            custodied_negative_tickets=['fixture-%d'%i for i in range(17)],
            terminal_tasks_sha256='a'*64, history_sha256='b'*64,
            v30_transition_sha256='c'*64, original_v2_custody_sha256=self.before['head_hash'], new_dispatches=0,
            scientific_first_use=False, v2_receipt_authorized=False)

    def test_real_cold_missing_v30_history_denied_without_any_write(self):
        with SingleOwner(self.path.with_suffix('.lock')):
            with self.assertRaises(route.MaintenanceDenied):
                route.commit_transition(self.db, self.proof, owner_witness=lambda: True)
        self.assertEqual(self.db.meta(), self.before)
        cold = Database.open_readonly(self.path)
        try:
            cold.verify()
            self.assertEqual(cold.meta(), self.before)
        finally:
            cold.close()

    def test_injected_verifier_failure_rolls_back_source_and_event(self):
        with SingleOwner(self.path.with_suffix('.lock')), patch.object(
                route, 'build_proof', return_value=self.proof), patch.object(
                self.db, 'verify', side_effect=RuntimeError('cold proof failure')):
            with self.assertRaisesRegex(RuntimeError, 'cold proof failure'):
                route.commit_transition(self.db, self.proof, owner_witness=lambda: True)
        self.db.verify()
        self.assertEqual(self.db.meta(), self.before)
        self.assertEqual(self.db.conn.execute(
            "SELECT COUNT(*) FROM events WHERE kind='SOURCE_TRANSITION_ADMITTED'").fetchone()[0], 0)

    def test_owner_revocation_at_each_boundary_prevents_commit(self):
        for values in ([False], [True, False], [True, True, False]):
            with self.subTest(values=values), SingleOwner(self.path.with_suffix('.lock')), patch.object(
                    route, 'build_proof', return_value=self.proof):
                from unittest.mock import Mock
                with patch.object(self.db, 'verify'):
                    with self.assertRaisesRegex(route.MaintenanceDenied, 'OWNER'):
                        route.commit_transition(self.db, self.proof,
                                                owner_witness=Mock(side_effect=values))
            self.db.verify()
            self.assertEqual(self.db.meta(), self.before)

    def test_stale_proof_cannot_replace_current_history(self):
        with SingleOwner(self.path.with_suffix('.lock')), patch.object(
                route, 'build_proof', return_value=self.proof):
            for key in ('history_sha256', 'prior_event_head_sha256', 'terminal_tasks_sha256'):
                with self.subTest(key=key), self.assertRaisesRegex(
                        route.MaintenanceDenied, 'APPROVAL_OR_LEDGER_DRIFT'):
                    route.commit_transition(self.db, {**self.proof, key:'e'*64},
                                            owner_witness=lambda: True)
        self.assertEqual(self.db.meta(), self.before)

    def test_cold_event_rejects_replay_authority_and_custody_changes(self):
        previous = [{'schema':'forge.f139.source-transition.v25',
                     'from_source_sha':'d'*40, 'to_source_sha':route.FROM_V30}]
        row = {'seq':383, 'prior_sha':self.proof['prior_event_head_sha256']}
        state = {k:self.proof[k] for k in ('verified_historical_tasks',
                 'custodied_negative_tasks', 'custodied_negative_tickets',
                 'terminal_tasks_sha256', 'history_sha256', 'v30_transition_sha256', 'original_v2_custody_sha256')}
        with patch.object(route, 'snapshot', return_value=state):
            route.verify_cold_event(self.db, row, self.proof, previous)
            for change in ({'new_dispatches':1}, {'scientific_first_use':True},
                           {'v2_receipt_authorized':True}, {'owner_event_id':0},
                           {'from_source_sha':'e'*40}, {'to_source_sha':route.FROM_V30},
                           {'history_sha256':'f'*64}, {'extra':'denied'}):
                with self.subTest(change=change), self.assertRaises(route.MaintenanceDenied):
                    route.verify_cold_event(self.db, row, {**self.proof, **change}, previous)
            with self.assertRaises(route.MaintenanceDenied):
                route.verify_cold_event(self.db, row, self.proof, previous+[self.proof])

    def test_original_mutex_cannot_be_substituted(self):
        with self.assertRaisesRegex(route.MaintenanceDenied, 'MUTEX'):
            route.commit_transition(self.db, self.proof, owner_witness=lambda: True)

    def test_snapshot_seals_only_terminal_historical_source_tasks_and_all_events(self):
        previous = [{'schema':'forge.f139.source-transition.v25',
                     'from_source_sha':'d'*40, 'to_source_sha':route.FROM_V30}]
        from f139.nci04_negative_owner_store import TICKET as FIRST
        from f139.nci04_split_negative_owner_store import TICKET as SECOND
        from f139.nci04_g49_prepost_negative import TICKET as PREPOST
        negatives = [FIRST, SECOND, PREPOST, 'g54'] + ['failed-%d'%i for i in range(13)]
        with self.db.transaction():
            for i, ticket in enumerate(negatives+['good-%d'%i for i in range(32)]):
                self.db.conn.execute('INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) VALUES(?,?,?,?,?)',
                    (ticket,'Wingless',route.FROM_V30,'QUARANTINED' if i<17 else 'VERIFIED','a'*64))
            self.db.event('SOURCE_TRANSITION_ADMITTED', previous[-1])
            for i in range(8):
                self.db.event('FREE_REASONER_ATTEMPTED', {'synthetic':i})
            self.db.event('NATIVE_RENEWAL_PROPOSAL_VALIDATED', {'synthetic':'stranded'})
        row={'seq':self.db.meta()['head_seq']+1}
        with patch.object(route, 'terminal_custody', return_value={'sha':'d'*64}), patch.object(self.db, 'verified_native_provider_failures',
                return_value={t:None for t in negatives[4:]}) as failures, patch.object(
                route, 'g54_original_canonical', return_value={'ticket':'g54'}) as ambiguous:
            first=route.snapshot(self.db,row,previous)
            failures.assert_called_once_with(through_seq=row['seq'])
            ambiguous.assert_called_once_with(self.db,through_seq=row['seq'])
            self.assertEqual(first['custodied_negative_tasks'],17)
            self.assertEqual(first['verified_historical_tasks'],32)
            # A new release's tasks must not corrupt the old frozen task seal.
            self.db.conn.execute('INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) VALUES(?,?,?,?,?)',
                                ('future','Yggdrasil','f'*40,'READY','a'*64))
            self.assertEqual(route.snapshot(self.db,row,previous),first)
            self.db.conn.execute("UPDATE tasks SET stage='READY' WHERE ticket='good-0'")
            with self.assertRaisesRegex(route.MaintenanceDenied,'NOT_TERMINAL'):
                route.snapshot(self.db,row,previous)

class InstallerWorkflowTests(unittest.TestCase):
    def test_inert_parse_of_every_installer_run_block(self):
        if os.name != 'nt':
            self.skipTest('Windows PowerShell parser requires Windows')
        raw=(ROOT/'.github/workflows/f139-v31-original-owner-release.yml').read_text()
        blocks=raw.split('        run: |\n')[1:]
        executable=shutil.which('powershell.exe')
        self.assertIsNotNone(executable)
        for block in blocks:
            with tempfile.TemporaryDirectory() as d:
                script=Path(d)/'parse-only.ps1'
                script.write_text('\n'.join(line[10:] if line.startswith(' '*10) else line
                                             for line in block.splitlines()),encoding='utf-8')
                parsed=subprocess.run([executable,'-NoProfile','-NonInteractive','-Command',
                    '$tokens=$null;$errors=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('
                    +'\''+str(script).replace("'","''")+'\',[ref]$tokens,[ref]$errors);'
                    'if($errors.Count){$errors|ForEach-Object{$_.Message};exit 1}'],
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
                self.assertEqual(parsed.returncode,0,parsed.stdout.decode(errors='replace'))

    def test_installer_requires_qualified_immutable_create_and_cold_backup(self):
        s=(ROOT/'.github/workflows/f139-v31-original-owner-release.yml').read_text()
        for token in ("$event.before -cne ('0'*40)", "$env:GITHUB_RUN_ATTEMPT -cne '1'",
                      'EXACT_QUALIFICATION_REQUIRED','FINAL_LINUX_WINDOWS_RECEIPTS_REQUIRED',
                      'bypass_actors', 'refs/heads/f139-owner-release-*',
                      'cold=Database.open_readonly(backup)', 'cold.verify()',
                      'if($mutationPossible) {','POSTMUTATION_EXISTING_TASK_DISABLED_AND_QUIESCENT'):
            self.assertIn(token,s)
        self.assertLess(s.index('cold.verify()'),s.index('$mutationPossible=$true'))
        self.assertEqual(s.count('-m f139.nci04_v31_original_owner_transition_cli '),1)
        self.assertNotIn('issue_comment:',s)
        self.assertNotIn('schedule:',s)

class ReceiptMaintenanceBoundaryTests(unittest.TestCase):
    def test_exact_current_workflow_routes_only_v31_and_no_live_task_dispatch(self):
        import ast, fnmatch, re
        routed=[]
        for version in (27,28,29,30,31):
            s=(ROOT/f'.github/workflows/f139-v{version}-original-owner-release.yml').read_text()
            patterns=ast.literal_eval(re.findall(r'^    branches: (\[.*\])$',s,re.M)[0])
            if any(fnmatch.fnmatchcase('f139-owner-release-'+'f'*40,p) for p in patterns):
                routed.append(version)
        self.assertEqual(routed,[31])
        s=(ROOT/'f139/nci04_v31_original_owner_transition_cli.py').read_text()
        self.assertNotIn('run_once(',s)
        self.assertNotIn('.dispatch',s)
        self.assertLess(s.index('reconcile(copy,'),s.index('result=reconcile(db,'))
        self.assertLess(s.index('F139_V31_AUTHENTICATED_RECEIPT_AND_TRANSITION_REHEARSAL=PASS'),s.index('result=reconcile(db,'))
        workflow=(ROOT/'.github/workflows/f139-v31-original-owner-release.yml').read_text()
        self.assertIn('ZeroFreeBSTR($ptr)',workflow)
        self.assertIn('Remove-Item Env:F139_WORKER_HMAC_KEY',workflow)
        self.assertNotIn('--key ',workflow)

    def test_unqualified_waiting_source_has_no_provider_call_or_write(self):
        from f139.nci04_v31_original_owner_transition_cli import reconcile
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as d:
            db=Database.initialize(Path(d)/'fixture.sqlite',route.FROM_V30)
            try:
                before=db.meta().copy()
                api=Mock()
                with self.assertRaises(ValueError):
                    reconcile(db,api,db.filename,'isolated-fixture-key-'+'x'*32)
                self.assertEqual(db.meta(),before)
                self.assertEqual(api.mock_calls,[])
            finally:
                db.close()
