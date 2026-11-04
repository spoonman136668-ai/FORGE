"""V35 boundary falsification; fixtures confer no original-owner authority."""
import ast
from contextlib import closing
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
from unittest.mock import patch

from f139 import nci04_v35_source_transition as route
from f139 import test_nci04_v34_source_transition as prior
from f139.local_controller import Database, SingleOwner, v2_owner_terminal_release_guard
from f139 import nci04_genenv_owner_backend as backend

ROOT = Path(__file__).resolve().parents[1]


def proof(seq=876):
    doc = prior.proof(seq)
    doc.update(schema=route.SCHEMA, from_source_sha=route.FROM_V34,
               verified_historical_tasks=72, custodied_negative_tasks=35,
               custodied_negative_tickets=['negative-%d'%i for i in range(35)])
    doc['v34_transition_sha256'] = doc.pop('v33_transition_sha256')
    doc['preserved_counters'].update(MODEL_DRAFT_ATTEMPTED=64,
                                     MODEL_DRAFT_AUTHENTICATED=64)
    return doc


class V35Tests(unittest.TestCase):
    def test_cold_contract_requires_new_exact_prefix_seal_and_fences(self):
        previous=[dict(schema=prior.route.SCHEMA,from_source_sha=prior.route.FROM_V33,
                       to_source_sha=route.FROM_V34)]
        doc=proof()
        row=dict(seq=877,prior_sha=doc['prior_event_head_sha256'])
        keys=('verified_historical_tasks','custodied_negative_tasks','custodied_negative_tickets',
              'terminal_tasks_sha256','history_sha256','v34_transition_sha256','preserved_counters')
        with patch.object(route,'snapshot',return_value={k:doc[k] for k in keys}):
            route.verify_cold_event(None,row,doc,previous)
            for delta in ({'schema':prior.route.SCHEMA}, {'original_head_seq':875},
                          {'from_source_sha':prior.route.FROM_V33},
                          {'v34_transition_sha256':'0'*64}, {'history_sha256':'0'*64},
                          {'scientific_first_use':True}, {'new_dispatches':1},
                          {'v2_receipt_authorized':True}, {'owner_event_id':True},
                          {'generation_mechanism_sha256':'invalid'},
                          {'preserved_counters':{}}, {'extra':False}):
                with self.subTest(delta=delta),self.assertRaises(route.MaintenanceDenied):
                    route.verify_cold_event(None,row,{**doc,**delta},previous)
            with self.assertRaises(route.MaintenanceDenied):
                route.verify_cold_event(None,row,doc,previous+[doc])

    def test_spent_counters_never_roll_over_or_accept_partial_publication(self):
        counts=proof()['preserved_counters']
        self.assertTrue(route.preserved_counters_valid(counts))
        for delta in ({'FREE_REASONER_ATTEMPTED':7},{'FREE_REASONER_ATTEMPTED':9},
                      {'MODEL_DRAFT_AUTHENTICATED':63},{'G3_DRAFT_ATTEMPTED':0},
                      {'MODEL_DRAFT_ATTEMPTED':61,'MODEL_DRAFT_AUTHENTICATED':61}):
            self.assertFalse(route.preserved_counters_valid({**counts,**delta}))

    def test_unsealed_real_database_and_stale_or_revoked_proof_cannot_mutate(self):
        with tempfile.TemporaryDirectory() as temp, closing(Database.initialize(
                Path(temp)/'fixture.sqlite',route.FROM_V34)) as db:
            db.enable(legacy_suspended=True)
            original=db.meta().copy()
            with SingleOwner(db.filename.with_suffix('.lock')):
                with self.assertRaises(route.MaintenanceDenied):
                    route.commit_transition(db,proof(),owner_witness=lambda:True)
                with patch.object(route,'build_proof',return_value=proof()):
                    with self.assertRaisesRegex(route.MaintenanceDenied,'APPROVAL_OR_LEDGER_DRIFT'):
                        route.commit_transition(db,{**proof(),'history_sha256':'0'*64},
                                                owner_witness=lambda:True)
                    with self.assertRaises(route.MaintenanceDenied):
                        route.commit_transition(db,proof(),owner_witness=lambda:False)
                    with patch.object(db,'verify',side_effect=ValueError('post failure')):
                        with self.assertRaisesRegex(ValueError,'post failure'):
                            route.commit_transition(db,proof(),owner_witness=lambda:True)
            self.assertEqual(db.meta(),original)
            db.verify()

    def test_genuine_v34_seal_dynamic_history_and_every_terminal_are_preserved(self):
        conn=sqlite3.connect(':memory:'); self.addCleanup(conn.close)
        conn.row_factory=sqlite3.Row
        conn.execute('CREATE TABLE events(seq INTEGER,kind TEXT,sha TEXT,payload TEXT)')
        conn.execute('CREATE TABLE tasks(ticket TEXT,stage TEXT,run_id INTEGER,evidence_sha TEXT,evidence_dir TEXT,source_sha TEXT)')
        previous=[dict(schema=prior.route.SCHEMA,from_source_sha=prior.route.FROM_V33,
                       to_source_sha=route.FROM_V34)]
        from f139.nci04_negative_owner_store import TICKET as FIRST
        from f139.nci04_split_negative_owner_store import TICKET as SECOND
        from f139.nci04_g49_prepost_negative import TICKET as PREPOST
        failures=['fixture-negative-%02d'%i for i in range(31)]
        negatives=sorted([FIRST,SECOND,PREPOST,'fixture-g54']+failures)
        for i in range(1,877):
            kind=('FREE_REASONER_ATTEMPTED' if i<=8 else
                  'MODEL_DRAFT_ATTEMPTED' if i<=72 else
                  'MODEL_DRAFT_AUTHENTICATED' if i<=136 else
                  'G3_DRAFT_ATTEMPTED' if i==137 else
                  'G3_DRAFT_AUTHENTICATED' if i==138 else 'FIXTURE')
            payload='{}'
            if i==855: kind,payload='SOURCE_TRANSITION_ADMITTED',json.dumps(previous[-1])
            conn.execute('INSERT INTO events VALUES(?,?,?,?)',(i,kind,'a'*64,payload))
        for i,ticket in enumerate(['verified-%02d'%i for i in range(72)]+negatives):
            conn.execute('INSERT INTO tasks VALUES(?,?,?,?,?,?)',(ticket,
                'QUARANTINED' if ticket in negatives else 'VERIFIED',i+1,'b'*64,
                'fixture-custody',route.FROM_V34))
        db=SimpleNamespace(conn=conn,verified_native_provider_failures=lambda **_:failures)
        row=dict(seq=877,prior_sha='a'*64)
        with patch.object(route,'g54_original_canonical',return_value={'ticket':'fixture-g54'}):
            result=route.snapshot(db,row,previous)
            self.assertEqual(result['custodied_negative_tickets'],negatives)
            self.assertEqual(result['verified_historical_tasks'],72)
            self.assertEqual(result['preserved_counters']['MODEL_DRAFT_AUTHENTICATED'],64)
            conn.execute("INSERT INTO tasks VALUES('future','WAIT_PROVIDER',NULL,NULL,NULL,?)",('f'*40,))
            self.assertEqual(route.snapshot(db,row,previous),result)
            conn.execute("UPDATE tasks SET stage='WAIT_PROVIDER' WHERE ticket=?",(negatives[0],))
            with self.assertRaisesRegex(route.MaintenanceDenied,'HISTORICAL_TASK_NOT_TERMINAL'):
                route.snapshot(db,row,previous)
            conn.execute("UPDATE tasks SET stage='QUARANTINED' WHERE ticket=?",(negatives[0],))
            conn.execute("UPDATE events SET payload='{}' WHERE seq=855")
            with self.assertRaisesRegex(route.MaintenanceDenied,'V34_SEAL_DRIFT'):
                route.snapshot(db,row,previous)

    def test_new_modern_guard_and_binary_custody_require_complete_proof(self):
        with tempfile.TemporaryDirectory() as temp, closing(Database.initialize(
                Path(temp)/'fixture.sqlite','f'*40)) as db:
            db.enable(legacy_suspended=True); db.event('SOURCE_TRANSITION_ADMITTED',proof())
            with patch.object(db,'verify'), patch('f139.local_controller.g54_original_canonical'), \
                    patch('f139.nci04_g49_prepost_negative.verify_g49_custody',return_value=True), \
                    patch('f139.nci04_owner_ledger.verify_native_activation',return_value=True):
                self.assertTrue(v2_owner_terminal_release_guard('f'*40,db))
                db.event('SOURCE_TRANSITION_ADMITTED',dict(schema=route.SCHEMA,to_source_sha='f'*40))
                self.assertFalse(v2_owner_terminal_release_guard('f'*40,db))
        class Connection:
            def execute(self,*_): return self
            def fetchone(self): return {'payload':json.dumps(proof())}
        db=SimpleNamespace(conn=Connection(),verify=lambda:None)
        backend.typed_generation_custody(db,'f'*40,'1'*64)
        with self.assertRaisesRegex(backend.BackendUnavailable,'TYPED_MECHANISM_DRIFT'):
            backend.typed_generation_custody(db,'f'*40,'2'*64)

    def test_both_exact_guards_have_identical_baseline_manifest_and_unique_route(self):
        text=(ROOT/'.github/workflows/f139-v35-release-qualification.yml').read_text()
        self.assertEqual(re.findall(r"baseline = '([a-f0-9]{40})'",text),
                         ['98d2d5f7231de1b6f070ae97aebafd6b2dc9dcfc']*2)
        manifests=[ast.literal_eval(s) for s in re.findall(
            r'expected_paths = (\{.*?\n          \})',text,re.S)]
        self.assertEqual(len(manifests),2); self.assertEqual(manifests[0],manifests[1])
        self.assertEqual(manifests[0], {
            '.github/workflows/f139-v35-release-qualification.yml',
            'docs/F139-V35-ORIGINAL-OWNER-FEEDBACK-RELEASE.md',
            'f139/test_nci04_v35_source_transition.py',
        })
        self.assertEqual(text.count('assert routed == [35]'),2)
        self.assertEqual(text.count('for version in (27, 28, 29, 30, 31, 32, 33, 34, 35):'),2)
        old=(ROOT/'.github/workflows/f139-v34-original-owner-release.yml').read_text()
        patterns=ast.literal_eval(re.findall(r'^    branches: (\[.*\])$',old,re.M)[0])
        self.assertEqual(patterns,['f139-owner-release-'+route.FROM_V34])

    def test_busy_owner_refuses_before_any_controller_mutation_and_never_retries(self):
        """Frozen release rule: one nonblocking owner lock admission before all writes."""
        text=(ROOT/'.github/workflows/f139-v35-original-owner-release.yml').read_text()
        self.assertIn("github.event.created == true",text)
        self.assertIn("GITHUB_RUN_ATTEMPT -cne '1'",text)
        self.assertEqual(text.count('$ownerLock.Lock(0,1)'),1)
        lock=text.index('$ownerLock.Lock(0,1)')
        busy=text.index("throw 'F139_V35_OWNER_TICK_BUSY_NO_MUTATION'")
        disable=text.index('Disable-ScheduledTask -TaskName $name')
        stop=text.index('Stop-ScheduledTask -TaskName $name')
        policy_write=text.index('gh api -X PATCH')
        self.assertLess(lock,busy)
        self.assertLess(busy,disable)
        self.assertLess(disable,policy_write)
        self.assertLess(disable,stop)
        self.assertNotIn('Start-Sleep',text[:lock])
        self.assertNotIn('Disable-ScheduledTask',text[:lock])
        self.assertNotIn('gh api -X PATCH',text[:lock])
        self.assertEqual(text.count('group: forge-f139-original-owner-release'),1)

    def test_idle_gate_denies_each_single_unsatisfied_prerequisite(self):
        """Development fixture: V35 admission remains strict for every idle condition."""
        base = dict(source_sha=route.FROM_V34, head_seq=922,
                    enabled=1, legacy_suspended=1)
        cases = (
            ("source", {"source_sha": "0"*40}, None, (), True),
            ("ledger_floor", {"head_seq": 855}, None, (), True),
            ("enabled", {"enabled": 0}, None, (), True),
            ("legacy_suspended", {"legacy_suspended": 0}, None, (), True),
            ("ready", {}, object(), (), True),
            ("active", {}, None, (object(),), True),
            ("activation", {}, None, (), False),
        )
        for name, overrides, ready, active, activation in cases:
            with self.subTest(prerequisite=name):
                readings = []
                meta = {**base, **overrides}
                db = SimpleNamespace(
                    verify=lambda: readings.append("verify"),
                    meta=lambda: dict(meta),
                    ready=lambda: ready,
                    actives=lambda: list(active))
                with patch.object(route, "verify_native_activation",
                                  return_value=activation):
                    with self.assertRaisesRegex(
                            route.MaintenanceDenied,
                            "F139_V35_IDLE_GENUINE_V34_REQUIRED"):
                        route.validate_idle(db)
                self.assertEqual(readings, ["verify"])
        readings = []
        good = SimpleNamespace(verify=lambda: readings.append("verify"),
            meta=lambda: dict(base), ready=lambda: None, actives=lambda: [])
        with patch.object(route, "verify_native_activation",
                          return_value=True) as native_check:
            route.validate_idle(good)
            native_check.assert_called_once_with(good)
        self.assertEqual(readings, ["verify"])

    def test_idle_gate_stops_on_database_integrity_failure(self):
        """A failed original SQLite verification cannot be treated as idle."""
        def deny_verification():
            raise ValueError("integrity failed")
        db = SimpleNamespace(verify=deny_verification)
        with patch.object(route, "verify_native_activation") as native_check:
            with self.assertRaisesRegex(ValueError, "integrity failed"):
                route.validate_idle(db)
            native_check.assert_not_called()

    def test_idle_diagnostic_is_readonly_and_does_not_authorize(self):
        """The report describes seven guards; validation still rejects each failure."""
        baseline = dict(source_sha=route.FROM_V34, head_seq=922,
                        enabled=1, legacy_suspended=1)
        cases = (
            ("v34_source", {"source_sha": "0"*40}, None, (), True),
            ("history_floor", {"head_seq": 855}, None, (), True),
            ("owner_enabled", {"enabled": 0}, None, (), True),
            ("legacy_suspended", {"legacy_suspended": 0}, None, (), True),
            ("no_ready", {}, object(), (), True),
            ("no_active", {}, None, (object(),), True),
            ("native_activation", {}, None, (), False),
        )
        for rejected, overrides, ready, active, activated in cases:
            with self.subTest(failed_predicate=rejected):
                verified = []
                record = {**baseline, **overrides}
                db = SimpleNamespace(
                    filename=Path("f139-diagnostic-fixture.sqlite"),
                    verify=lambda: verified.append("verified"),
                    meta=lambda: dict(record), ready=lambda: ready,
                    actives=lambda: list(active))
                with patch.object(route, "Database", SimpleNamespace), \
                     patch.object(route.SingleOwner, "held", return_value=True), \
                     patch.object(route, "verify_native_activation",
                                  return_value=activated):
                    diagnostic = route.idle_gate_predicates(db)
                    self.assertEqual(len(diagnostic), 7)
                    self.assertFalse(diagnostic[rejected])
                    self.assertTrue(all(value for key, value in diagnostic.items()
                                        if key != rejected))
                    with self.assertRaisesRegex(route.MaintenanceDenied,
                                                "IDLE_GENUINE_V34_REQUIRED"):
                        route.validate_idle(db)
                self.assertEqual(verified, ["verified", "verified"])
        self.assertEqual(baseline["source_sha"], route.FROM_V34)

    def test_idle_diagnostic_denies_unlocked_or_invalid_database(self):
        db = SimpleNamespace(filename=Path("f139-diagnostic-fixture.sqlite"),
                             verify=lambda: None)
        with patch.object(route, "Database", SimpleNamespace), \
             patch.object(route.SingleOwner, "held", return_value=False):
            with self.assertRaisesRegex(route.MaintenanceDenied,
                                        "ORIGINAL_DATABASE_MUTEX_REQUIRED"):
                route.idle_gate_predicates(db)
        with patch.object(route, "Database", SimpleNamespace), \
             patch.object(route.SingleOwner, "held", return_value=True), \
             patch.object(db, "verify", side_effect=ValueError("integrity failure")):
            with self.assertRaisesRegex(ValueError, "integrity failure"):
                route.idle_gate_predicates(db)

    def test_failed_idle_workflow_reports_predicates_but_always_reraises(self):
        text=(ROOT/'.github/workflows/f139-v35-original-owner-release.yml').read_text()
        self.assertEqual(text.count("                  validate_idle(db)"), 1)
        self.assertIn("except MaintenanceDenied as exc:", text)
        self.assertIn("if str(exc) == \"F139_V35_IDLE_GENUINE_V34_REQUIRED\":", text)
        self.assertIn("diagnostic = idle_gate_predicates(db)", text)
        self.assertIn("F139_V35_IDLE_GATE_READONLY=", text)
        self.assertIn("F139_V35_IDLE_GATE_DIAGNOSTIC=UNAVAILABLE", text)
        self.assertIn("                      raise\n                  original=db.meta().copy()", text)
        self.assertNotIn("Start-Sleep", text[:text.index("$ownerLock.Lock(0,1)")])
        self.assertEqual(text.count('$ownerLock.Lock(0,1)'), 1)

    @unittest.skipUnless(os.name=='nt','Windows PowerShell parsing only')
    def test_new_installer_parses_in_both_shells_without_execution(self):
        text=(ROOT/'.github/workflows/f139-v35-original-owner-release.yml').read_text()
        block=text.split('        run: |\n')[1]
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'inert.ps1'
            p.write_text('\n'.join(x[10:] if x.startswith(' '*10) else x
                                   for x in block.splitlines()),encoding='utf-8')
            for shell in ('powershell.exe','pwsh.exe'):
                command="$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('"+str(p).replace("'","''")+"',[ref]$t,[ref]$e);if($e.Count){$e|%{$_.Message};exit 1}"
                out=subprocess.run([shutil.which(shell),'-NoProfile','-NonInteractive','-Command',command],
                                   capture_output=True,text=True,timeout=30)
                self.assertEqual(out.returncode,0,out.stdout+out.stderr)
