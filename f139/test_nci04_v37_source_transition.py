"""V37 falsification fixtures confer no live source or scientific authority."""
from contextlib import closing
import fnmatch
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from f139 import nci04_v37_source_transition as route
from f139 import nci04_v37_original_owner_transition_cli as cli
from f139 import check_v37_release_source as source_guard
from f139 import test_nci04_v36_source_transition as prior
from f139.local_controller import Database, SingleOwner, v2_owner_terminal_release_guard
from f139 import nci04_genenv_owner_backend as backend

ROOT = Path(__file__).resolve().parents[1]
STATE = ('verified_historical_tasks', 'custodied_negative_tasks', 'custodied_negative_tickets',
         'terminal_tasks_sha256', 'history_sha256', 'v36_transition_sha256', 'preserved_counters',
         'i1464_negative_event_sha256', 'i1464_original_receipt_sha256')


def proof(seq=1238):
    doc = prior.proof(seq)
    doc.update(schema=route.SCHEMA, from_source_sha=route.FROM_V36,
               verified_historical_tasks=89, custodied_negative_tasks=56,
               custodied_negative_tickets=['negative-%d'%i for i in range(56)],
               i1464_negative_event_sha256=route.I1464_EVENT,
               i1464_original_receipt_sha256=route.I1464_RECEIPT)
    doc['v36_transition_sha256'] = doc.pop('v35_transition_sha256')
    doc['preserved_counters'].update(MODEL_DRAFT_ATTEMPTED=95, MODEL_DRAFT_AUTHENTICATED=95)
    return doc


class V37ContractTests(unittest.TestCase):
    def previous(self):
        return [dict(schema=prior.route.SCHEMA, from_source_sha=prior.route.FROM_V35,
                     to_source_sha=route.FROM_V36)]

    def test_cold_event_binds_predecessor_prefix_receipt_and_every_authority_fence(self):
        doc = proof(); row = dict(seq=1239, prior_sha=doc['prior_event_head_sha256'])
        with patch.object(route, 'snapshot', return_value={k:doc[k] for k in STATE}):
            route.verify_cold_event(None, row, doc, self.previous())
            for delta in ({'schema':prior.route.SCHEMA}, {'original_head_seq':1237},
                    {'original_head_seq':True}, {'from_source_sha':'e'*40},
                    {'to_source_sha':route.FROM_V36}, {'owner_event_id':True},
                    {'v36_transition_sha256':'0'*64}, {'history_sha256':'0'*64},
                    {'i1464_negative_event_sha256':'0'*64},
                    {'i1464_original_receipt_sha256':'0'*64}, {'scientific_first_use':True},
                    {'new_dispatches':1}, {'v2_receipt_authorized':True},
                    {'genenv_executable_sha256':'bad'}, {'genenv_toolchain':'wrong'},
                    {'generation_mechanism_sha256':'bad'}, {'preserved_counters':{}}, {'extra':False}):
                with self.subTest(delta=delta), self.assertRaises(route.MaintenanceDenied):
                    route.verify_cold_event(None, row, {**doc,**delta}, self.previous())
            with self.assertRaises(route.MaintenanceDenied):
                route.verify_cold_event(None, row, doc, self.previous()+[doc])

    def test_lifetime_spend_and_unfinished_publication_never_reset(self):
        counts=proof()['preserved_counters']; self.assertTrue(route.preserved_counters_valid(counts))
        self.assertTrue(route.preserved_counters_valid({**counts,'MODEL_DRAFT_ATTEMPTED':200,'MODEL_DRAFT_AUTHENTICATED':200}))
        for delta in ({'FREE_REASONER_ATTEMPTED':7},{'FREE_REASONER_ATTEMPTED':9},
                      {'MODEL_DRAFT_AUTHENTICATED':94}, {'MODEL_DRAFT_ATTEMPTED':94,'MODEL_DRAFT_AUTHENTICATED':94},
                      {'G3_DRAFT_ATTEMPTED':True},{'extra':0}):
            self.assertFalse(route.preserved_counters_valid({**counts,**delta}))

    def history(self):
        # In-memory contract fixture only; not a forged original hash chain.
        conn=sqlite3.connect(':memory:');self.addCleanup(conn.close);conn.row_factory=sqlite3.Row
        conn.execute('CREATE TABLE events(seq INTEGER,kind TEXT,sha TEXT,prior_sha TEXT,payload TEXT)')
        conn.execute('CREATE TABLE tasks(ticket TEXT,stage TEXT,run_id INTEGER,evidence_sha TEXT,evidence_dir TEXT,source_sha TEXT,lane TEXT,started_at TEXT,quarantine_reason TEXT,completed_at TEXT)')
        from f139.nci04_negative_owner_store import TICKET as FIRST
        from f139.nci04_split_negative_owner_store import TICKET as SECOND
        from f139.nci04_g49_prepost_negative import TICKET as PREPOST
        failures=['provider-negative-%02d'%i for i in range(51)]
        negatives=sorted([FIRST,SECOND,PREPOST,'fixture-g54',route.I1464_TICKET]+failures)
        for i in range(1,1239):
            kind=('FREE_REASONER_ATTEMPTED' if i<=8 else 'MODEL_DRAFT_ATTEMPTED' if i<=103
                  else 'MODEL_DRAFT_AUTHENTICATED' if i<=198 else 'G3_DRAFT_ATTEMPTED' if i==199
                  else 'G3_DRAFT_AUTHENTICATED' if i==200 else 'FIXTURE')
            sha=prior_sha='a'*64; payload='{}'
            if i==945:kind,payload='SOURCE_TRANSITION_ADMITTED',json.dumps(self.previous()[-1])
            if i==1084:
                kind,sha,prior_sha='ATTEMPT_QUARANTINED',route.I1464_EVENT,prior.route.I1464_PRIOR
                payload=json.dumps({'ticket':route.I1464_TICKET,'reason':'AMBIGUOUS_START_NO_PROVIDER_RUN'})
            conn.execute('INSERT INTO events VALUES(?,?,?,?,?)',(i,kind,sha,prior_sha,payload))
        for i,ticket in enumerate(['positive-%02d'%i for i in range(89)]+negatives):
            special=ticket==route.I1464_TICKET
            conn.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?)',(ticket,
                'QUARANTINED' if ticket in negatives else 'VERIFIED',None if special else i+1,
                None if special else 'b'*64,None if special else '/fixture-only',prior.route.FROM_V35 if special else route.FROM_V36,'Yggdrasil',
                '2026-11-04T09:35:01.440970Z' if special else None,
                'AMBIGUOUS_START_NO_PROVIDER_RUN' if special else None,None))
        db=SimpleNamespace(conn=conn,verified_native_provider_failures=lambda **_:failures)
        return db,negatives

    def test_full_terminal_history_and_exact_negative_are_preserved(self):
        db,negatives=self.history();row=dict(seq=1239,prior_sha='a'*64)
        with patch.object(route,'g54_original_canonical',return_value={'ticket':'fixture-g54'}):
            result=route.snapshot(db,row,self.previous())
            self.assertEqual(result['verified_historical_tasks'],89)
            self.assertEqual(result['custodied_negative_tickets'],negatives)
            self.assertEqual(result['i1464_negative_event_sha256'],route.I1464_EVENT)
            for statement in (
                "UPDATE tasks SET stage='WAIT_PROVIDER' WHERE ticket='positive-00'",
                "DELETE FROM tasks WHERE ticket='provider-negative-00'",
                "UPDATE events SET payload='{}' WHERE seq=945",
                "UPDATE events SET kind='FIXTURE' WHERE seq=103",
                "UPDATE events SET sha='bad' WHERE seq=1238"):
                with self.subTest(statement=statement):
                    db.conn.execute('SAVEPOINT falsify');db.conn.execute(statement)
                    with self.assertRaises(route.MaintenanceDenied):route.snapshot(db,row,self.previous())
                    db.conn.execute('ROLLBACK TO falsify');db.conn.execute('RELEASE falsify')

    def test_ambiguous_negative_cannot_be_rebound_replayed_or_have_forged_receipt(self):
        db,_=self.history();self.assertEqual(route.i1464_negative_anchor(db,1239),route.I1464_TICKET)
        statements=(
            "UPDATE events SET sha='wrong' WHERE seq=1084",
            "UPDATE events SET prior_sha='wrong' WHERE seq=1084",
            "UPDATE tasks SET run_id=42 WHERE ticket=?",
            "UPDATE tasks SET stage='READY' WHERE ticket=?",
            "UPDATE tasks SET source_sha='wrong' WHERE ticket=?",
            "UPDATE tasks SET evidence_sha='unexpected' WHERE ticket=?",
            "UPDATE tasks SET started_at='wrong' WHERE ticket=?")
        for sql in statements:
            with self.subTest(sql=sql):
                db.conn.execute('SAVEPOINT falsify');db.conn.execute(sql,(route.I1464_TICKET,) if '?' in sql else ())
                with self.assertRaises(route.MaintenanceDenied):route.i1464_negative_anchor(db,1239)
                db.conn.execute('ROLLBACK TO falsify');db.conn.execute('RELEASE falsify')
        payload=json.dumps({'ticket':route.I1464_TICKET,'reason':'AMBIGUOUS_START_NO_PROVIDER_RUN'})
        db.conn.execute("UPDATE events SET kind='ATTEMPT_QUARANTINED',payload=? WHERE seq=1238",(payload,))
        with self.assertRaisesRegex(route.MaintenanceDenied,'NOT_UNIQUE'):route.i1464_negative_anchor(db,1239)

    def test_unsealed_real_database_and_revoked_proof_cannot_mutate(self):
        with tempfile.TemporaryDirectory() as temp,closing(Database.initialize(Path(temp)/'fixture.sqlite',route.FROM_V36)) as db:
            db.enable(legacy_suspended=True);before=db.meta().copy()
            with SingleOwner(db.filename.with_suffix('.lock')):
                with self.assertRaises(route.MaintenanceDenied):route.commit_transition(db,proof(),owner_witness=lambda:True)
                with self.assertRaises(route.MaintenanceDenied):route.commit_transition(db,proof(),owner_witness=lambda:False)
                with patch.object(route,'build_proof',return_value=proof()):
                    with self.assertRaisesRegex(route.MaintenanceDenied,'APPROVAL_OR_LEDGER_DRIFT'):
                        route.commit_transition(db,{**proof(),'history_sha256':'0'*64},owner_witness=lambda:True)
                    with patch.object(db,'verify',side_effect=ValueError('post failure')):
                        with self.assertRaisesRegex(ValueError,'post failure'):
                            route.commit_transition(db,proof(),owner_witness=lambda:True)
            self.assertEqual(db.meta(),before);db.verify()

    def test_readonly_preflight_rejects_writer_and_never_grants_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'fixture.sqlite'
            with closing(Database.initialize(path,route.FROM_V36)) as writer:
                writer.enable(legacy_suspended=True)
                with self.assertRaisesRegex(route.MaintenanceDenied,'READONLY_ORIGINAL'):
                    route.readonly_snapshot(writer)
            before=hashlib.sha256(path.read_bytes()).hexdigest()
            with closing(Database.open_readonly(path)) as db:
                with self.assertRaises(route.MaintenanceDenied):route.readonly_snapshot(db)
                with patch.object(route,'validate_idle'),patch.object(route,'snapshot',return_value={k:proof()[k] for k in STATE}):
                    report=route.readonly_snapshot(db)
                self.assertFalse(report['source_transition_authorized'])
                self.assertEqual(report['owner_mutations'],0);self.assertEqual(report['new_dispatches'],0)
                with self.assertRaises(sqlite3.OperationalError):db.conn.execute("DELETE FROM events")
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),before)

    def test_preflight_cli_never_calls_transition_and_always_closes(self):
        fake=SimpleNamespace(close=Mock(),conn=Mock())
        report={'source_transition_authorized':False}
        with patch.object(cli,'guarded_transition') as commit,patch.object(Database,'open_readonly',return_value=fake),\
             patch.object(route,'readonly_snapshot',return_value=report),patch('sys.stdout',new_callable=io.StringIO) as out:
            cli.main(['--db','fixture.sqlite','--target','f'*40,'--preflight-only'])
            self.assertFalse(json.loads(out.getvalue())['source_transition_authorized']);commit.assert_not_called();fake.close.assert_called_once()
        from f139.nci04_v32_original_owner_transition_cli import guarded_transition
        with patch('f139.nci04_v32_original_owner_transition_cli.os.name','posix'):
            with self.assertRaisesRegex(route.MaintenanceDenied,'WINDOWS_EXACT_TARGET'):
                guarded_transition(None,None,'f'*40,42,None,route.TOOLCHAIN,_contract=route)

    def test_private_rehearsal_refuses_an_original_writer_and_preflight_failure_closes(self):
        with tempfile.TemporaryDirectory() as temp,closing(Database.initialize(Path(temp)/'fixture.sqlite',route.FROM_V36)) as db:
            before=db.meta().copy()
            with self.assertRaisesRegex(route.MaintenanceDenied,'READONLY_ORIGINAL_REQUIRED'):
                cli.rehearse_private_history(db,'f'*40,42)
            self.assertEqual(db.meta(),before)
        fake=SimpleNamespace(close=Mock(),conn=Mock())
        with patch.object(cli,'guarded_transition') as commit,patch.object(Database,'open_readonly',return_value=fake),\
             patch.object(route,'readonly_snapshot',side_effect=ValueError('snapshot rejected')):
            with self.assertRaisesRegex(ValueError,'snapshot rejected'):
                cli.main(['--db','fixture.sqlite','--target','f'*40,'--preflight-only','--rehearse-copy'])
            commit.assert_not_called();fake.close.assert_called_once();fake.conn.rollback.assert_called_once()

    def test_new_modern_guard_and_generator_custody_require_exact_new_proof(self):
        with tempfile.TemporaryDirectory() as temp,closing(Database.initialize(Path(temp)/'fixture.sqlite','f'*40)) as db:
            db.enable(legacy_suspended=True);db.event('SOURCE_TRANSITION_ADMITTED',proof())
            with patch.object(db,'verify'),patch('f139.local_controller.g54_original_canonical'),\
                 patch('f139.nci04_g49_prepost_negative.verify_g49_custody',return_value=True),\
                 patch('f139.nci04_owner_ledger.verify_native_activation',return_value=True):
                self.assertTrue(v2_owner_terminal_release_guard('f'*40,db))
                db.event('SOURCE_TRANSITION_ADMITTED',dict(schema=route.SCHEMA,to_source_sha='f'*40))
                self.assertFalse(v2_owner_terminal_release_guard('f'*40,db))
        class Connection:
            def execute(self,*_):return self
            def fetchone(self):return {'payload':json.dumps(proof())}
        fake=SimpleNamespace(conn=Connection(),verify=lambda:None)
        backend.typed_generation_custody(fake,'f'*40,'1'*64)
        with self.assertRaises(backend.BackendUnavailable):backend.typed_generation_custody(fake,'f'*40,'2'*64)

    def test_activation_carries_only_the_exact_new_certified_negative_set(self):
        # Exercise the real activation transaction with synthetic foundation
        # and archive witnesses. These fixtures deliberately grant no live right.
        import test_nci04_owner_ledger as fixture
        from f139 import nci04_owner_ledger as ledger
        from f139.nci04_negative_owner_store import TICKET as FIRST
        from f139.nci04_split_negative_owner_store import TICKET as SECOND
        from f139.nci04_g49_prepost_negative import TICKET as PREPOST
        for mode in ('v32','old_schema','unknown_negative'):
            with self.subTest(mode=mode):
                f=fixture.LedgerTests('test_admit_exactly_once_and_verify_original_ledger');f.setUp()
                try:
                    db=f.db
                    db.conn.execute("UPDATE meta SET source_sha=?",('f'*40,))
                    negatives=sorted([FIRST,SECOND,PREPOST,'fixture-g54',route.I1464_TICKET,'provider-negative'])
                    for ticket in negatives+(['unknown-negative'] if mode=='unknown_negative' else []):
                        db.conn.execute("INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) VALUES(?,?,?,'QUARANTINED',?)",
                            (ticket,'Yggdrasil',route.FROM_V36,'a'*64))
                    doc={**proof(), 'custodied_negative_tasks':len(negatives), 'custodied_negative_tickets':negatives}
                    if mode=='old_schema':doc['schema']=prior.prior.route.SCHEMA
                    db.event('SOURCE_TRANSITION_ADMITTED',doc)
                    before=db.meta().copy()
                    approval=dict(schema=ledger.APPROVAL_SCHEMA,source_sha='f'*40,
                        expected_event_head_sha256=before['head_hash'],native_development_approved=True,
                        scientific_first_use=False,create_controller=False,paid_api_calls=0)
                    with patch.object(db,'verify'),patch.object(db,'verified_native_provider_failures',return_value={'provider-negative':('a'*40,'b'*64)}),\
                         patch('f139.nci04_negative_owner_store.verify_original_negative_custody',return_value=True),\
                         patch('f139.nci04_split_negative_owner_store.verify_second_negative_custody',return_value=True),\
                         patch('f139.nci04_g49_prepost_negative.verify_g49_custody',return_value=True),\
                         patch('f139.local_controller.g54_original_canonical',return_value={'ticket':'fixture-g54'}),\
                         patch.object(prior.route,'i1464_negative_anchor',return_value=route.I1464_TICKET) as anchor:
                        if mode=='v32':
                            self.assertTrue(ledger.activate_native(db,approval))
                            self.assertEqual(db.meta()['head_seq'],before['head_seq']+1)
                            anchor.assert_called_once()
                        else:
                            with self.assertRaisesRegex(ledger.NativeLedgerDenied,'UNVERIFIED_HISTORICAL_TASK'):
                                ledger.activate_native(db,approval)
                            self.assertEqual(db.meta(),before)
                            if mode=='old_schema':anchor.assert_not_called()
                finally:f.doCleanups()


class V37ReleaseSurfaceTests(unittest.TestCase):
    def test_only_new_installer_routes_future_refs_and_old_route_is_frozen(self):
        source_guard.verify(ROOT,get=self.git_fixture)
        old=(ROOT/'.github/workflows/f139-v36-original-owner-release.yml').read_text()
        self.assertIn("branches: ['f139-owner-release-"+route.FROM_V36+"']",old)

    def git_fixture(self,*args):
        if args==('rev-parse','HEAD'):return 'f'*40
        if args[0]=='status':return ''
        if args[0]=='merge-base':return source_guard.BASELINE
        if args[0]=='diff':return '\n'.join(sorted(source_guard.PATHS))
        raise AssertionError(args)

    def test_dirty_wrong_baseline_and_scope_expansion_fail_closed(self):
        for kind in ('status','merge-base','diff'):
            def bad(*args):
                if args[0]==kind:return ('dirty' if kind=='status' else 'e'*40 if kind=='merge-base' else self.git_fixture(*args)+'\nf139/nci04_worker_v2.py')
                return self.git_fixture(*args)
            with self.subTest(kind=kind),self.assertRaises(ValueError):source_guard.verify(ROOT,get=bad)

    @unittest.skipUnless(os.environ.get('GITHUB_ACTIONS')=='true' and
        os.environ.get('GITHUB_HEAD_REF')=='engineering/f139-v37-public-order-owner-handoff-20261105',
        'Exact V37 release branch manifest; installed-source guard remains unconditional')
    def test_real_ci_source_manifest_and_ancestry(self):source_guard.verify(ROOT)

    def test_running_owner_preflight_precedes_every_stop_and_policy_write(self):
        text=(ROOT/'.github/workflows/f139-v37-original-owner-release.yml').read_text()
        lock=text.index('[F139OriginalOwnerMutex]::Acquire(');preflight=text.index('--preflight-only')
        self.assertLess(lock,preflight);self.assertLess(preflight,text.index('Disable-ScheduledTask -TaskName $name'))
        self.assertLess(preflight,text.index('gh api -X PATCH'))
        self.assertIn('F139_V37_PREFLIGHT_LEASE_MOVED',text)
        self.assertIn('with closing(sqlite3.connect(str(backup))) as out:',text)
        self.assertNotIn('Start-Sleep',text[:lock]);self.assertEqual(text.count('[F139OriginalOwnerMutex]::Acquire('),1)
        self.assertIn("GITHUB_RUN_ATTEMPT -cne '1'",text)
        self.assertNotIn('\n  schedule:',text);self.assertNotIn('\n  workflow_dispatch:',text)
        self.assertIn('NATIVE_WINDOWS', (ROOT/'.github/workflows/forge-f139-source-qualification.yml').read_text())

    def test_readonly_surface_cannot_stop_or_patch_the_original_owner(self):
        text=(ROOT/'.github/workflows/f139-v37-original-owner-release.yml').read_text()
        job=text.split('  running-owner-readonly-preflight:',1)[1]
        for forbidden in ('Disable-ScheduledTask','Stop-ScheduledTask','Start-ScheduledTask',
                          'Enable-ScheduledTask','gh api -X','Import-Clixml','--event-id'):
            self.assertNotIn(forbidden,job)
        self.assertIn('issues: read',job);self.assertNotIn('issues: write',job)
        self.assertIn('--preflight-only',job)
        self.assertIn("F139_V37_READONLY_EXACT_QUALIFICATION_REQUIRED",job)

    @unittest.skipUnless(os.name=='nt','Windows PowerShell 5.1 and pwsh parsing only')
    def test_new_installer_parses_in_both_shells_without_execution(self):
        text=(ROOT/'.github/workflows/f139-v37-original-owner-release.yml').read_text()
        blocks=[]
        for part in text.split('        run: |\n')[1:]:
            lines=[]
            for line in part.splitlines():
                if line and not line.startswith(' '*10):break
                lines.append(line[10:] if line.startswith(' '*10) else line)
            blocks.append('\n'.join(lines))
        self.assertEqual(len(blocks),2)
        with tempfile.TemporaryDirectory() as temp:
            for index,block in enumerate(blocks):
                p=Path(temp)/('inert-'+str(index)+'.ps1');p.write_text(block,encoding='utf-8')
                for shell in ('powershell.exe','pwsh.exe'):
                    command="$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('"+str(p).replace("'","''")+"',[ref]$t,[ref]$e);if($e.Count){$e|%{$_.Message};exit 1}"
                    out=subprocess.run([shutil.which(shell),'-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=30)
                    self.assertEqual(out.returncode,0,out.stdout+out.stderr)



if __name__=='__main__':unittest.main()
