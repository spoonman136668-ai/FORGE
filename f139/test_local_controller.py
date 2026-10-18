"""Native F139 controller acceptance: genuine SQLite transactions, fake GH receipts."""
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import zipfile

from local_controller import (Database, F139Error, GitHub, LIMIT_PER_DAY, REPO, SCHEMA,
                              SingleOwner, canonical, hash_bytes, receipt_from_zip,
                              run_once, store_evidence, ZERO)

SHA = 'e1b16d0a4097e9fd3d61c9ee635486a72395cf4b'
KEY = 'f139-test-local-key-not-a-real-secret-0123456789'
NOW = '2026-10-18T15:00:00Z'
TASKS = [
    {'ticket':'f139-wingless-dev-001', 'lane':'Wingless', 'source_sha':SHA},
    {'ticket':'f139-yggdrasil-dev-002', 'lane':'Yggdrasil', 'source_sha':SHA},
]


def artifact(task, run_id, oslabel, epoch=1):
    payload = canonical({
        'schema':'forge.f139.development-worker-receipt.v1',
        'ticket':task['ticket'],'lane':task['lane'],'epoch':epoch,
        'run_id':run_id,'os':oslabel,'source_sha':SHA,
        'development_only':True,'scientific_first_use_authorized':False,
        'scientific_originals_dispatched':0,'accepted_ref_mutations':0,
        'paid_model_calls':0,'codex_calls':0
    })
    digest=(hash_bytes(payload)+'  f139-receipt.json\n').encode()
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('f139-receipt.json',payload)
        z.writestr('f139-receipt.sha256',digest)
    return mem.getvalue()


class FakeGitHub:
    def __init__(self):
        self.head=SHA
        self.dispatches=[]
        self.mode='waiting'
        self.fail_launch=False
        self.corrupt=False
        self.stalled=False

    def protected_main(self): return self.head
    def dispatch(self,ticket,lane,source,epoch,signature):
        self.dispatches.append((ticket,lane,source,epoch,signature))
        if self.fail_launch: raise F139Error('F139_GITHUB_API_TIMEOUT')
    def candidates(self,ticket,started_at):
        if self.stalled:return None
        index=[v[0] for v in self.dispatches].index(ticket) if any(v[0]==ticket for v in self.dispatches) else None
        if index is None:return None
        return {'id':1000+index,'ticket':ticket}
    def run_proof(self,run,ticket,source,started_at):
        if self.mode=='waiting':return None
        if self.mode=='failed':raise F139Error('F139_FAILED_OR_CANCELLED_NO_REPLAY')
        run_id=run['id']
        names=['ubuntu-latest','windows-latest']
        arts=[{'id':100+run_id+i,'name':'forge-f139-dev-receipt-'+os,'expired':False,
               'workflow_run':{'id':run_id,'head_sha':SHA},'digest':'sha256:'+hash_bytes(artifact(
                   {'ticket':ticket,'lane':next(q[1] for q in self.dispatches if q[0]==ticket)},run_id,os)),
               'size_in_bytes':len(artifact({'ticket':ticket,'lane':next(q[1] for q in self.dispatches if q[0]==ticket)},run_id,os))}
              for i,os in enumerate(names)]
        self.current={a['id']:artifact({'ticket':ticket,'lane':next(q[1] for q in self.dispatches if q[0]==ticket)},run_id,os) for a,os in zip(arts,names)}
        return run_id,arts
    def artifact(self,id):
        blob=self.current[id]
        if self.corrupt:return blob+b'x'
        return blob


class SQLiteControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='f139-control-')
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'state.sqlite'
        self.db=Database.initialize(self.path,SHA)
        self.addCleanup(self.db.close)
        self.gh=FakeGitHub()
        self.db.enqueue(TASKS,'f'*64)
        self.db.enable(legacy_suspended=True)

    def call(self): return run_once(self.db,self.gh,self.path,KEY,now=NOW)

    def test_two_distinct_auto_successions_and_durable_zip_receipts(self):
        self.assertEqual(self.call()['disposition'],'DEVELOPMENT_DISPATCHED_ONCE')
        self.assertEqual(self.call()['disposition'],'WORKER_RUNNING_NO_REDISPATCH')
        self.assertEqual(len(self.gh.dispatches),1)
        self.gh.mode='complete'
        result=self.call()
        self.assertEqual(result['ticket'],TASKS[1]['ticket'])
        self.assertEqual(len(self.gh.dispatches),2)
        self.assertEqual(self.call()['disposition'],'QUEUE_EMPTY_NO_SCIENCE')
        self.assertEqual(len(self.gh.dispatches),2)
        self.assertTrue(self.db.meta()['head_seq']>=8)
        self.assertEqual([x['stage'] for x in self.db.status()['tasks']],['VERIFIED','VERIFIED'])
        for task in TASKS:
            evidence=list((self.path.parent/'evidence'/task['ticket']).rglob('*.zip'))
            self.assertEqual(len(evidence),2)
        reopened=Database(self.path);reopened.verify();reopened.close()

    def test_restart_after_start_risk_never_relaunches(self):
        self.gh.fail_launch=True
        with self.assertRaisesRegex(F139Error,'TIMEOUT'):self.call()
        self.assertEqual(self.db.status()['tasks'][0]['stage'],'START_RISK')
        self.db.close()
        self.db=Database(self.path)
        self.gh.fail_launch=False
        self.gh.stalled=True
        for _ in range(5):
            self.assertEqual(self.call()['disposition'],'START_RISK_PENDING_NO_REDISPATCH')
        self.assertEqual(len(self.gh.dispatches),1)

    def test_failed_worker_quarantines_only_this_attempt_and_succeeds_other_lane(self):
        self.call()
        self.gh.mode='failed'
        with self.assertRaisesRegex(F139Error,'NO_REPLAY'):self.call()
        self.assertEqual(self.db.status()['tasks'][0]['stage'],'QUARANTINED')
        self.assertEqual(self.call()['ticket'],TASKS[1]['ticket'])
        self.assertEqual(len(self.gh.dispatches),2)
        self.assertNotIn(TASKS[0]['ticket'],[x[0] for x in self.gh.dispatches[1:]])

    def test_corrupt_provider_artifacts_are_quarantined(self):
        self.call();self.gh.mode='complete';self.gh.corrupt=True
        with self.assertRaisesRegex(F139Error,'DIGEST_DRIFT'):self.call()
        self.assertEqual(self.db.status()['tasks'][0]['stage'],'QUARANTINED')
        self.assertEqual(len(self.gh.dispatches),1)

    def test_main_sha_drift_fails_before_start(self):
        self.gh.head='0'*40
        with self.assertRaisesRegex(F139Error,'MAIN_SOURCE_DRIFT'):self.call()
        self.assertEqual(len(self.gh.dispatches),0)

    def test_db_missing_and_existing_init_rejected(self):
        with self.assertRaisesRegex(F139Error,'DATABASE_ALREADY_EXISTS'):Database.initialize(self.path,SHA)
        with self.assertRaisesRegex(F139Error,'DATABASE_MISSING'):Database(self.path.with_name('missing.sqlite'))

    def test_modified_event_or_head_is_quarantined(self):
        self.call()
        with self.assertRaises(sqlite3.IntegrityError):self.db.conn.execute('DELETE FROM events')
        self.db.conn.execute('UPDATE meta SET head_hash=? WHERE id=1',('a'*64,))
        with self.assertRaisesRegex(F139Error,'ROLLBACK'):self.db.verify()

    def test_same_database_cannot_enqueue_after_cutover(self):
        with self.assertRaisesRegex(F139Error,'QUEUE_MANIFEST_LOCKED'):self.db.enqueue(TASKS,'a'*64)

    def test_source_unrecognized_or_duplicate_task_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'empty.sqlite';other=Database.initialize(p,SHA)
            try:
                with self.assertRaisesRegex(F139Error,'TASK_UNQUALIFIED'):
                    other.enqueue(TASKS+[TASKS[0]],'a'*64)
                self.assertEqual(other.conn.execute('SELECT COUNT(*) FROM tasks').fetchone()[0],0)
            finally:other.close()

    def test_two_process_lock_is_exclusive(self):
        path=self.path.with_suffix('.lock')
        with SingleOwner(path):
            with self.assertRaisesRegex(F139Error,'ALREADY_RUNNING'):
                with SingleOwner(path):pass
        with SingleOwner(path):pass

    def test_active_provider_job_never_replays_on_restart(self):
        self.call();self.db.close();self.db=Database(self.path)
        for _ in range(3):self.call()
        self.assertEqual(len(self.gh.dispatches),1)

    def test_schema_untrusted_lane_and_no_delete(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.conn.execute('INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha) VALUES(?,?,?,?,?)',
                                 ('f139-forbidden-lane-003','Science',SHA,'READY','a'*64))
        with self.assertRaises(sqlite3.IntegrityError):self.db.conn.execute('DELETE FROM tasks')


class ProviderProofTests(unittest.TestCase):
    def test_zip_receipt_exact_identity(self):
        task=TASKS[0]
        blob=artifact(task,123,'windows-latest')
        item={'digest':'sha256:'+hash_bytes(blob),'size_in_bytes':len(blob)}
        self.assertEqual(receipt_from_zip(blob,item,task,123,'windows-latest')['run_id'],123)
        with self.assertRaisesRegex(F139Error,'DIGEST_DRIFT'):
            receipt_from_zip(blob+b'x',item,task,123,'windows-latest')

    def test_git_provider_accepts_expected_run_but_not_spoof(self):
        github=GitHub(runner=lambda args: b'{}')
        run={'display_title':'F139 '+TASKS[0]['ticket'],'event':'workflow_dispatch',
             'name':'FORGE F139 development worker','path':'.github/workflows/forge-f139-development-worker.yml',
             'head_sha':SHA,'head_branch':'main','run_attempt':1,'id':123,'created_at':NOW,
             'status':'in_progress'}
        self.assertIsNone(github.run_proof(run,TASKS[0]['ticket'],SHA,NOW))
        for key,val in [('head_sha','0'*40),('event','schedule'),('run_attempt',2),('display_title','other')]:
            bad={**run,key:val}
            with self.subTest(key=key),self.assertRaisesRegex(F139Error,'SPOOFED'):
                github.run_proof(bad,TASKS[0]['ticket'],SHA,NOW)

if __name__=='__main__':unittest.main()
