"""Isolated regression for the observed READY/V2 release-guard stall."""
from __future__ import annotations
import ast
from contextlib import closing
import fnmatch
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from f139 import nci04_v30_source_transition as route
from f139.local_controller import Database, SingleOwner, v2_owner_terminal_release_guard

ROOT = Path(__file__).resolve().parent.parent

class PendingTransferTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Construct and verify the exact original 376-event ledger once.
        # No mutable database handles or WAL files are shared between tests.
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'template.sqlite'
            db = Database.initialize(path, route.FROM_V29)
            try:
                db.enable(legacy_suspended=True)
                for i in range(373):
                    db.event('UNTRUSTED_TEST_FIXTURE', {'i': i})
                # Verify the admissible 374-event prefix before the test's intentionally
                # incomplete native admission is added in each independent test.
                db.verify()
                if db.meta()['head_seq'] != 374:
                    raise AssertionError('ORIGINAL_FIXTURE_HEAD_DRIFT')
                cls._fixture_head = db.meta()['head_hash']
            finally:
                db.close()
            if any((Path(str(path) + suffix)).exists() for suffix in ('-wal','-shm')):
                raise AssertionError('ORIGINAL_FIXTURE_UNCHECKPOINTED_WAL')
            cls._fixture_bytes = path.read_bytes()

    @classmethod
    def tearDownClass(cls):
        del cls._fixture_bytes
        del cls._fixture_head
        super().tearDownClass()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / 'isolated.sqlite'
        # A fresh physical file/connection per test, never a shared live DB.
        with self.path.open('xb') as stream:
            stream.write(type(self)._fixture_bytes)
        self.db = Database(self.path)  # Verify the valid cold source prefix.
        self.addCleanup(self.db.close)
        self.assertEqual(self.db.meta()['head_seq'], 374)
        self.assertEqual(self.db.meta()['head_hash'], type(self)._fixture_head)
        # Preserve the exact original incomplete admission and task records.
        # Those are the negative-control fixture; a full post-admission verify
        # must reject their deliberately missing custody fields.
        self.db.conn.execute('INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) VALUES(?,?,?,?,?)',
                             (route.TICKET,'Yggdrasil',route.FROM_V29,'READY','a'*64))
        self.db.event('NATIVE_DEVELOPMENT_ADMITTED', dict(ticket=route.TICKET,
                      issue_number=1358,source_sha=route.FROM_V29,manifest_sha256='a'*64))
        self.db.event('TASK_INTAKE',dict(ticket=route.TICKET))
        self.assertEqual(self.db.meta()['head_seq'],376)
        self.assertEqual(self.db.conn.execute('PRAGMA synchronous').fetchone()[0], 2)

    def test_exact_unclaimed_identity_is_read_only_and_does_not_reissue(self):
        before = self.db.conn.total_changes
        value = route._pending(self.db,377,unclaimed=True)
        self.assertEqual(value['ticket'],route.TICKET)
        self.assertEqual(value['admission_event_seq'],375)
        self.assertEqual(self.db.conn.total_changes,before)
        self.assertEqual(self.db.meta()['head_seq'],376)

    def test_claimed_or_ambiguous_attempt_cannot_cross_maintenance(self):
        self.db.event('BEFORE_DISPATCH_INTENT',dict(ticket=route.TICKET))
        self.db.conn.execute("UPDATE tasks SET stage='START_RISK',started_at='2026-11-02T00:00:00Z'")
        with self.assertRaisesRegex(route.MaintenanceDenied,'ONLY_NEVER_CLAIMED'):
            route._pending(self.db,377,unclaimed=True)
        with self.assertRaisesRegex(route.MaintenanceDenied,'SPENT_ATTEMPT'):
            route._pending(self.db,379)

    def test_preexisting_post_or_terminal_cannot_be_carried(self):
        for kind in ('DISPATCH_POST_RETURNED','PROVIDER_VERIFIED_TERMINAL','ATTEMPT_QUARANTINED'):
            with self.subTest(kind=kind):
                self.db.event(kind,dict(ticket=route.TICKET))
                with self.assertRaises(route.MaintenanceDenied):
                    route._pending(self.db,self.db.meta()['head_seq']+1,unclaimed=True)

    def test_once_only_post_transition_claim_does_not_change_original_source(self):
        original=route._pending(self.db,377)
        self.db.event('UNTRUSTED_TRANSITION_FIXTURE',{})
        self.db.event('BEFORE_DISPATCH_INTENT',dict(ticket=route.TICKET))
        self.db.conn.execute("UPDATE tasks SET stage='START_RISK'")
        self.assertEqual(route._pending(self.db,377),original)
        self.db.event('DISPATCH_POST_RETURNED',dict(ticket=route.TICKET))
        self.db.conn.execute("UPDATE tasks SET stage='WAIT_PROVIDER'")
        self.assertEqual(route._pending(self.db,377),original)
        self.db.event('BEFORE_DISPATCH_INTENT',dict(ticket=route.TICKET))
        with self.assertRaisesRegex(route.MaintenanceDenied,'REPLAY'):
            route._pending(self.db,377)

    def test_no_implicit_source_exception_without_exact_transition(self):
        self.assertIsNone(route.carried_source(self.db,route.TICKET))
        self.assertIsNone(route.carried_source(self.db,'another-ticket'))
        pending=route._pending(self.db,377)
        self.db.event('SOURCE_TRANSITION_ADMITTED',dict(schema=route.SCHEMA,
                      to_source_sha='f'*40,pending_native=pending))
        self.assertIsNone(route.carried_source(self.db,route.TICKET))
        self.db.conn.execute("UPDATE meta SET source_sha=?",('f'*40,))
        self.assertEqual(route.carried_source(self.db,route.TICKET),route.FROM_V29)
        self.db.conn.execute("UPDATE tasks SET manifest_sha=?",('b'*64,))
        with self.assertRaisesRegex(route.MaintenanceDenied,'IDENTITY'):
            route.carried_source(self.db,route.TICKET)

    def test_rewinding_ready_after_claim_is_rejected(self):
        self.db.event('UNTRUSTED_TRANSITION_FIXTURE',{})
        self.db.event('BEFORE_DISPATCH_INTENT',dict(ticket=route.TICKET))
        with self.assertRaisesRegex(route.MaintenanceDenied,'REPLAY'):
            route._pending(self.db,377)

    def test_real_missing_history_fails_without_writes(self):
        before=self.db.meta().copy()
        with SingleOwner(self.path.with_suffix('.lock')):
            with self.assertRaises(ValueError):
                route.build_proof(self.db,'f'*40,1)
        self.assertEqual(self.db.meta(),before)

class ModernV2GuardTests(unittest.TestCase):
    def test_sealed_modern_release_does_not_stall_at_v18(self):
        with tempfile.TemporaryDirectory() as d, closing(
                Database.initialize(Path(d)/'fixture.sqlite',route.FROM_V29)) as db:
            db.enable(legacy_suspended=True)
            db.event('SOURCE_TRANSITION_ADMITTED',dict(schema='forge.f139.source-transition.v24',
                     to_source_sha=route.FROM_V29,v2_receipt_authorized=False))
            # Isolate release selection; full chain and all seals are tested
            # by Database.verify and by the original-snapshot installer rehearsal.
            with patch.object(db,'verify') as cold, patch(
                    'f139.local_controller.g54_original_canonical',return_value={}), patch(
                    'f139.nci04_g49_prepost_negative.verify_g49_custody',return_value=True), patch(
                    'f139.nci04_owner_ledger.verify_native_activation',return_value=True):
                self.assertTrue(v2_owner_terminal_release_guard(route.FROM_V29,db))
                cold.assert_called_once()
                self.assertFalse(v2_owner_terminal_release_guard('e'*40,db))
            with patch.object(db,'verify',side_effect=ValueError('broken seal')):
                self.assertFalse(v2_owner_terminal_release_guard(route.FROM_V29,db))

    def test_old_worker_identity_survives_new_owner_source_for_both_signed_receipts(self):
        from f139.test_nci04_g38_owner_terminal import G38AtomicOwnerTests
        from f139.test_nci04_owner_issue import MAIN
        fixture=G38AtomicOwnerTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        db=fixture.db
        db.conn.execute('UPDATE meta SET source_sha=?',('f'*40,))
        from f139.nci04_g38_owner_terminal import settle_original_v2, G38Denied
        from f139.test_nci04_owner_issue import HMAC
        from f139.test_nci04_g32_owner_custody import RUN
        with patch.object(db,'verify'), patch(
                'f139.nci04_g32_owner_custody.verify_native_activation',return_value=True):
            with self.assertRaisesRegex(G38Denied,'EXACT_WAIT_PROVIDER'):
                fixture.apply()
            with patch('f139.nci04_g38_owner_terminal.carried_source',return_value=MAIN), patch(
                    'f139.nci04_g32_owner_custody.carried_source',return_value=MAIN):
                result=fixture.apply()
                self.assertEqual(result['outcome'],'VERIFIED')
                event=db.conn.execute("SELECT payload FROM events WHERE kind='NATIVE_V_TWO_PROVIDER_CUSTODY'").fetchone()
                self.assertEqual(json.loads(event[0])['source_sha'],MAIN)
                self.assertEqual(db.meta()['source_sha'],'f'*40)
                with self.assertRaisesRegex(G38Denied,'EXACT_WAIT_PROVIDER'):
                    fixture.apply()

class ActivationCarryTests(unittest.TestCase):
    def test_pending_activation_requires_explicit_verified_carry_and_keeps_task_bytes(self):
        from f139.test_nci04_owner_ledger import LedgerTests
        from f139.nci04_owner_ledger import admit_native_issue, activate_native, NativeLedgerDenied
        fixture=LedgerTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        db=fixture.db
        self.assertTrue(admit_native_issue(db,fixture.native,'2026-11-02T00:00:00Z'))
        before=[tuple(r) for r in db.conn.execute('SELECT * FROM tasks ORDER BY ticket')]
        approval=fixture.approval()
        with self.assertRaisesRegex(NativeLedgerDenied,'PREEXISTING_PENDING_WORK'):
            activate_native(db,approval)
        with patch('f139.nci04_v30_source_transition.carried_source',return_value=fixture.native.source_sha):
            self.assertTrue(activate_native(db,approval))
        self.assertEqual([tuple(r) for r in db.conn.execute('SELECT * FROM tasks ORDER BY ticket')],before)


class ColdTransitionTests(unittest.TestCase):
    def test_exact_boundary_and_predecessor_are_not_inferred_from_source_label(self):
        previous=[dict(schema='forge.f139.source-transition.v24',
                       from_source_sha='e'*40,to_source_sha=route.FROM_V29)]
        state=dict(verified_historical_tasks=31,custodied_negative_tasks=17,
                   custodied_negative_tickets=['negative'],terminal_tasks_sha256='a'*64,
                   history_sha256='b'*64,v29_transition_sha256='c'*64,pending_native={'ticket':route.TICKET})
        doc=dict(schema=route.SCHEMA,from_source_sha=route.FROM_V29,to_source_sha='f'*40,
                 owner_event_id=1,prior_event_head_sha256=route.HEAD,**state,new_dispatches=0,
                 scientific_first_use=False,v2_receipt_authorized=False)
        row=dict(seq=377,prior_sha=route.HEAD)
        with patch.object(route,'snapshot',return_value=state):
            route.verify_cold_event(None,row,doc,previous)
            for change in ({'new_dispatches':1},{'v2_receipt_authorized':True},
                           {'scientific_first_use':True},{'from_source_sha':'e'*40},
                           {'history_sha256':'d'*64},{'pending_native':{}},{'owner_event_id':0}):
                with self.subTest(change=change),self.assertRaises(route.MaintenanceDenied):
                    route.verify_cold_event(None,row,{**doc,**change},previous)
            with self.assertRaises(route.MaintenanceDenied):
                route.verify_cold_event(None,{**row,'seq':378},doc,previous)
            with self.assertRaises(route.MaintenanceDenied):
                route.verify_cold_event(None,row,doc,previous+[doc])

class InstallerTests(unittest.TestCase):
    def test_only_current_immutable_release_installer_receives_new_push(self):
        release='f139-owner-release-b419300f61a86d387bc4b630a9850eced8b8bb75'
        routed=[]
        for version in (27,28,29,30):
            text=(ROOT/f'.github/workflows/f139-v{version}-original-owner-release.yml').read_text()
            patterns=ast.literal_eval(re.findall(r'^    branches: (\[.*\])$',text,re.M)[0])
            if any(fnmatch.fnmatchcase(release,p) for p in patterns):
                routed.append(version)
        self.assertEqual(routed,[30])

    def test_original_snapshot_carry_rehearsal_precedes_first_live_mutation(self):
        text=(ROOT/'.github/workflows/f139-v30-original-owner-release.yml').read_text()
        self.assertLess(text.index('F139_V30_ORIGINAL_SNAPSHOT_UNCLAIMED_CARRY_REHEARSAL=PASS'),
                        text.index('$mutationPossible=$true'))
        self.assertIn("assert [tuple(r) for r in disposable.conn.execute('SELECT * FROM tasks ORDER BY ticket')]==before",text)
        self.assertIn('cold.verify()',text)
        self.assertIn("'@ | & $python -B - $dbPath $target",text)
        self.assertEqual(text.count('-m f139.nci04_v30_original_owner_transition_cli '),1)

    def test_windows_installer_is_inertly_parseable(self):
        import os,shutil,subprocess
        if os.name!='nt':
            self.skipTest('Windows parser requires Windows')
        text=(ROOT/'.github/workflows/f139-v30-original-owner-release.yml').read_text()
        for block in text.split('        run: |\n')[1:]:
            with tempfile.TemporaryDirectory() as d:
                path=Path(d)/'parse.ps1'
                path.write_text('\n'.join(x[10:] if x.startswith(' '*10) else x for x in block.splitlines()))
                cmd="$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('"+str(path)+"',[ref]$t,[ref]$e);if($e.Count){$e;exit 1}"
                result=subprocess.run([shutil.which('powershell.exe'),'-NoProfile','-NonInteractive','-Command',cmd],capture_output=True)
                self.assertEqual(result.returncode,0,result.stdout.decode(errors='replace'))
