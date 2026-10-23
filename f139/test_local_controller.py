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


def artifact(task, run_id, oslabel, epoch=1, issue=None):
    payload = canonical({
        'schema':'forge.f139.development-worker-receipt.v1',
        'ticket':task['ticket'],'lane':task['lane'],'epoch':epoch,
        'run_id':run_id,'os':oslabel,'source_sha':SHA,
        'development_only':True,'scientific_first_use_authorized':False,
        'scientific_originals_dispatched':0,'accepted_ref_mutations':0,
        'paid_model_calls':0,'codex_calls':0
    })
    diagnostic=None
    if issue is not None:
        diagnostic=canonical({
            "schema":"forge.f139.d2k.package-diagnostic.v1",
            "source_sha":SHA,"issue_number":int(issue["issue_number"]),
            "issue_id":int(issue["issue_id"]),"body_sha256":issue["body_sha256"],
            "target_package":issue["target_package"],"run_id":run_id,"os":oslabel,
            "outcome":"PASS","returncode":0,"duration_ms":17,
            "output_sha256":hash_bytes(b"test passed"),
            "output_excerpt":"test passed","output_bytes":11,
            "scientific_first_use":False,"paid_model_calls":0})
        payload=canonical({
            "schema":"forge.f139.d2k.package-diagnostic-receipt.v1",
            "ticket":task["ticket"],"lane":task["lane"],"epoch":epoch,
            "run_id":run_id,"os":oslabel,"source_sha":SHA,
            "issue_number":int(issue["issue_number"]),
            "issue_id":int(issue["issue_id"]),"body_sha256":issue["body_sha256"],
            "target_package":issue["target_package"],
            "diagnostic_sha256":hash_bytes(diagnostic),"outcome":"PASS",
            "development_only":True,"scientific_first_use_authorized":False,
            "scientific_originals_dispatched":0,"accepted_ref_mutations":0,
            "paid_model_calls":0,"codex_calls":0})
    digest=(hash_bytes(payload)+'  f139-receipt.json\n').encode()
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w',zipfile.ZIP_DEFLATED) as z:
        # Freeze synthetic ZIP metadata: repeated provider reads after a restart
        # must represent identical bytes, even when wall-clock seconds advance.
        # Production ZIP and receipt verification remain unchanged.
        for name, body in (
            ('f139-receipt.json', payload),
            ('f139-receipt.sha256', digest),
            *((('f139-diagnostic.json', diagnostic),) if diagnostic is not None else ()),
        ):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            z.writestr(entry, body, compress_type=zipfile.ZIP_DEFLATED)
    return mem.getvalue()


class DeterministicFixtureTests(unittest.TestCase):
    def test_archive_metadata_stable_across_regeneration(self):
        task = TASKS[0]
        first = artifact(task, 1000, 'windows-latest')
        second = artifact(task, 1000, 'windows-latest')
        self.assertEqual(first, second)
        with zipfile.ZipFile(io.BytesIO(first)) as bundle:
            self.assertTrue(all(member.date_time == (1980, 1, 1, 0, 0, 0)
                                for member in bundle.infolist()))


class FakeGitHub:
    def __init__(self):
        self.head=SHA
        self.dispatches=[]
        self.mode='waiting'
        self.fail_launch=False
        self.corrupt=False
        self.stalled=False
        self.d2k_issues=[]
        self.d2k_fields={}

    def protected_main(self): return self.head
    def d2k_eligible_issues(self, source):
        if source != self.head:raise F139Error('F139_D2K_SOURCE_DRIFT')
        return list(self.d2k_issues)
    def dispatch(self,ticket,lane,source,epoch,signature, *, d2k_fields=None):
        self.dispatches.append((ticket,lane,source,epoch,signature))
        if d2k_fields is not None: self.d2k_fields[ticket]=d2k_fields
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
        task={'ticket':ticket,'lane':next(q[1] for q in self.dispatches if q[0]==ticket)}
        issue=self.d2k_fields.get(ticket)
        labels=['ubuntu-latest','windows-latest']
        blobs={label:artifact(task,run_id,label,issue=issue) for label in labels}
        arts=[{'id':100+run_id+i,'name':'forge-f139-dev-receipt-'+label,
               'expired':False,'workflow_run':{'id':run_id,'head_sha':SHA},
               'digest':'sha256:'+hash_bytes(blobs[label]),
               'size_in_bytes':len(blobs[label])}
              for i,label in enumerate(labels)]
        self.current={item['id']:blobs[label] for item,label in zip(arts,labels)}
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
        self.addCleanup(lambda: self.db.close())
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

    def test_crash_after_complete_artifact_storage_recovers_without_redispatch(self):
        self.call()
        self.gh.mode='complete'
        task=dict(self.db.active())
        run=self.gh.candidates(task['ticket'],task['started_at'])
        rid,artifacts=self.gh.run_proof(run,task['ticket'],task['source_sha'],task['started_at'])
        archives={}
        for oslabel in ('ubuntu-latest','windows-latest'):
            item=next(x for x in artifacts if x['name']=='forge-f139-dev-receipt-'+oslabel)
            archives[oslabel]=self.gh.artifact(item['id'])
        stored,digest=store_evidence(self.path.parent,task['ticket'],rid,archives)
        self.assertTrue(Path(stored,'manifest.json').is_file())
        self.assertEqual(self.db.status()['tasks'][0]['stage'],'WAIT_PROVIDER')
        self.db.close()
        self.db=Database(self.path)
        result=self.call()
        self.assertEqual(result['ticket'],TASKS[1]['ticket'])
        self.assertEqual(len(self.gh.dispatches),2)
        recovered=dict(self.db.conn.execute('SELECT * FROM tasks WHERE ticket=?',(task['ticket'],)).fetchone())
        self.assertEqual(recovered['stage'],'VERIFIED')
        self.assertEqual(recovered['evidence_sha'],digest)
        self.assertEqual(recovered['run_id'],rid)

    def test_partial_custody_after_crash_quarantines_without_overwrite_or_replay(self):
        self.call()
        self.gh.mode='complete'
        first=TASKS[0]
        folder=self.path.parent/'evidence'/first['ticket']/'1000'
        folder.mkdir(parents=True)
        partial=b'partial-workstation-write'
        (folder/'ubuntu-latest.zip').write_bytes(partial)
        with self.assertRaisesRegex(F139Error,'EVIDENCE_RECOVERY_CONFLICT'):
            self.call()
        self.assertEqual((folder/'ubuntu-latest.zip').read_bytes(),partial)
        self.assertEqual(self.db.status()['tasks'][0]['stage'],'QUARANTINED')
        self.assertEqual(len(self.gh.dispatches),1)

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

    def test_main_sha_drift_blocks_new_work_without_replaying(self):
        self.gh.head='0'*40
        outcome=self.call()
        self.assertEqual(outcome['disposition'],'MAIN_SOURCE_DRIFT_DISPATCH_BLOCKED')
        self.assertEqual(outcome['owner_source_sha'],SHA)
        self.assertEqual(outcome['protected_main_sha'],'0'*40)
        self.assertEqual(len(self.gh.dispatches),0)
        self.db.verify()

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


class D2KCatalogTests(unittest.TestCase):
    def issue(self, number=1401, source=SHA, lane="Qualification"):
        return {
            "number":number, "id":90000 + number, "state":"open",
            "user":{"login":"spoonman136668-ai"},
            "author_association":"OWNER",
            "labels":[{"name":"f139-development-eligible"}],
            "body":json.dumps({
                "schema":"forge.f139.d2k.owner-development.v1",
                "source_sha":source, "lane":lane,
                "kind":"go-package-test-diagnostic",
                "target_package":"./planner",
                "scientific_first_use":False, "paid_model_calls":0
            },sort_keys=True)
        }

    def provider(self, issues):
        return GitHub(runner=lambda args: json.dumps(issues).encode())

    def test_owner_issue_catalog_accepts_only_exact_source_and_kind(self):
        first=self.issue()
        items=self.provider([first]).d2k_eligible_issues(SHA)
        self.assertEqual(len(items),1)
        self.assertTrue(items[0]["ticket"].startswith("f139-d2k-i1401-"+SHA[:12]+"-"))
        self.assertTrue(items[0]["ticket"].endswith(items[0]["body_sha256"][:8]))
        self.assertEqual(items[0]["lane"],"Qualification")
        self.assertEqual(items[0]["source_sha"],SHA)
        self.assertEqual(items[0]["kind"],"go-package-test-diagnostic")
        self.assertEqual(items[0]["target_package"],"./planner")
        for variant in (
            {**first,"author_association":"CONTRIBUTOR"},
            {**first,"user":{"login":"someone-else"}},
            {**first,"pull_request":{"url":"http://pr"}},
            {**first,"labels":[{"name":"anything-else"}]},
            {**first,"body":json.dumps({"schema":"forged"})},
            {**first,"body":json.dumps({**json.loads(first["body"]),
                "target_package":"./../../secrets"})},
            {**first,"body":json.dumps({**json.loads(first["body"]),
                "kind":"model-free-development-advisory"})},
            {**first,"body":json.dumps({**json.loads(first["body"]),
                "commands":["curl https://example.test"]})},
            {**first,"body":json.dumps({
                **json.loads(first["body"]), "scientific_first_use":True
            })},
            {**first,"body":json.dumps({
                **json.loads(first["body"]), "source_sha":"0"*40
            })},
        ):
            with self.subTest(variant=variant),self.assertRaisesRegex(
                    F139Error, "D2K_ISSUE"):
                self.provider([variant]).d2k_eligible_issues(SHA)

    def test_d2k_receipt_binds_diagnostic_bytes_to_issue(self):
        from verify_ticket import signature
        digest="a"*64
        fields={"issue_number":"1401","issue_id":"91401",
                "body_sha256":digest,"target_package":"./planner"}
        ticket="f139-d2k-i1401-"+SHA[:12]+"-"+digest[:8]
        task={"ticket":ticket,"lane":"Qualification","source_sha":SHA}
        blob=artifact(task,123,"ubuntu-latest",issue=fields)
        meta={"digest":"sha256:"+hash_bytes(blob),"size_in_bytes":len(blob)}
        result=receipt_from_zip(blob,meta,task,123,"ubuntu-latest",d2k_fields=fields)
        self.assertEqual(result["outcome"],"PASS")
        self.assertEqual(result["target_package"],"./planner")
        modified={**fields,"target_package":"./dreamrsi"}
        with self.assertRaisesRegex(F139Error,"D2K_RECEIPT_IDENTITY_OR_DIGEST"):
            receipt_from_zip(blob,meta,task,123,"ubuntu-latest",d2k_fields=modified)
        altered=io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(blob)) as original, zipfile.ZipFile(altered,"w") as out:
            for member in original.namelist():
                body=original.read(member)
                if member=="f139-diagnostic.json":
                    obj=json.loads(body);obj["outcome"]="TEST_FAILURE"
                    body=canonical(obj)
                out.writestr(member,body)
        rewritten=altered.getvalue()
        rewritten_meta={"digest":"sha256:"+hash_bytes(rewritten),
                        "size_in_bytes":len(rewritten)}
        with self.assertRaisesRegex(F139Error,"D2K_RECEIPT_IDENTITY_OR_DIGEST"):
            receipt_from_zip(rewritten,rewritten_meta,task,123,"ubuntu-latest",
                             d2k_fields=fields)

    def test_d2k_never_admits_on_unqualified_fresh_database(self):
        with tempfile.TemporaryDirectory(prefix="f139-d2k-catalog-") as tmp:
            dbpath=Path(tmp)/"state.sqlite"
            db=Database.initialize(dbpath,SHA)
            try:
                db.enable(legacy_suspended=True)
                issue=self.provider([self.issue()]).d2k_eligible_issues(SHA)[0]
                original=list(db.conn.execute("SELECT seq,sha FROM events"))
                with self.assertRaisesRegex(F139Error,"AUTHENTIC_SUCCESSION_REQUIRED"):
                    db.admit_d2k_issue(issue)
                self.assertEqual(list(db.conn.execute(
                    "SELECT seq,sha FROM events ORDER BY seq")),original)
                self.assertEqual(db.meta()["head_seq"],1)
                self.assertEqual(db.conn.execute(
                    "SELECT COUNT(*) FROM tasks").fetchone()[0],0)
            finally:db.close()


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
             'name':'F139 '+TASKS[0]['ticket'],'workflow_id':388797257,
             'path':'.github/workflows/forge-f139-development-worker.yml',
             'head_sha':SHA,'head_branch':'main','run_attempt':1,'id':123,'created_at':NOW,
             'status':'in_progress'}
        self.assertIsNone(github.run_proof(run,TASKS[0]['ticket'],SHA,NOW))
        for key,val in [('head_sha','0'*40),('event','schedule'),('run_attempt',2),
                        ('display_title','other'),('name','FORGE F139 development worker'),
                        ('workflow_id',0)]:
            bad={**run,key:val}
            with self.subTest(key=key),self.assertRaisesRegex(F139Error,'SPOOFED'):
                github.run_proof(bad,TASKS[0]['ticket'],SHA,NOW)

if __name__=='__main__':unittest.main()
