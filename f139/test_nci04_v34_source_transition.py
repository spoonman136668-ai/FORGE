"""V34 falsification and real lock interoperability; fixtures grant no live authority."""
from contextlib import closing
import ast
import fnmatch
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

from f139 import nci04_v34_source_transition as route
from f139.local_controller import Database, SingleOwner, v2_owner_terminal_release_guard
from f139.nci04_v32_original_owner_transition_cli import guarded_transition
from f139 import nci04_genenv_owner_backend as backend

ROOT = Path(__file__).resolve().parents[1]


def proof(seq=814):
    return dict(schema=route.SCHEMA, from_source_sha=route.FROM_V33,
        to_source_sha="f"*40, owner_event_id=41700000000, original_head_seq=seq,
        prior_event_head_sha256="a"*64, verified_historical_tasks=67,
        custodied_negative_tasks=33, custodied_negative_tickets=["negative-%d"%i for i in range(33)],
        terminal_tasks_sha256="b"*64, history_sha256="c"*64, v33_transition_sha256="d"*64,
        preserved_counters=dict(G3_DRAFT_ATTEMPTED=1, G3_DRAFT_AUTHENTICATED=1,
            MODEL_DRAFT_ATTEMPTED=57, MODEL_DRAFT_AUTHENTICATED=57, FREE_REASONER_ATTEMPTED=8),
        genenv_executable_sha256="e"*64, genenv_toolchain=route.TOOLCHAIN,
        generation_mechanism_sha256="1"*64, new_dispatches=0,
        scientific_first_use=False, v2_receipt_authorized=False)


class V34Tests(unittest.TestCase):
    def test_growing_source_history_never_resets_inference_or_unresolved_attempts(self):
        c=proof()["preserved_counters"]
        self.assertTrue(route.preserved_counters_valid(c))
        self.assertTrue(route.preserved_counters_valid({**c,
            "MODEL_DRAFT_ATTEMPTED":61, "MODEL_DRAFT_AUTHENTICATED":61}))
        for delta in ({"FREE_REASONER_ATTEMPTED":9}, {"FREE_REASONER_ATTEMPTED":7},
                      {"MODEL_DRAFT_AUTHENTICATED":56}, {"G3_DRAFT_ATTEMPTED":True},
                      {"extra":0}):
            with self.subTest(delta=delta):
                self.assertFalse(route.preserved_counters_valid({**c, **delta}))

    def test_cold_event_binds_actual_prefix_and_every_fence(self):
        previous=[dict(schema="forge.f139.source-transition.v28",
                       from_source_sha="2"*40, to_source_sha=route.FROM_V33)]
        keys=("verified_historical_tasks","custodied_negative_tasks","custodied_negative_tickets",
              "terminal_tasks_sha256","history_sha256","v33_transition_sha256","preserved_counters")
        for seq in (814,850):
            doc=proof(seq)
            row=dict(seq=seq+1, prior_sha=doc["prior_event_head_sha256"])
            with patch.object(route,"snapshot",return_value={k:doc[k] for k in keys}):
                route.verify_cold_event(None,row,doc,previous)
                for delta in ({"original_head_seq":seq-1},{"original_head_seq":True},
                    {"scientific_first_use":True},{"new_dispatches":1},
                    {"owner_event_id":True},{"v2_receipt_authorized":True},
                    {"to_source_sha":route.FROM_V33},{"from_source_sha":"3"*40},
                    {"history_sha256":"f"*64},{"genenv_executable_sha256":"bad"},
                    {"generation_mechanism_sha256":"bad"},{"genenv_toolchain":"other"},
                    {"preserved_counters":{}},{"extra":False}):
                    with self.subTest(delta=delta),self.assertRaises(route.MaintenanceDenied):
                        route.verify_cold_event(None,row,{**doc,**delta},previous)
                with self.assertRaises(route.MaintenanceDenied):
                    route.verify_cold_event(None,row,doc,previous+[doc])

    def test_real_database_without_genuine_v33_cannot_mutate_source(self):
        with tempfile.TemporaryDirectory() as temp, closing(Database.initialize(
                Path(temp)/"fixture.sqlite",route.FROM_V33)) as db:
            db.enable(legacy_suspended=True)
            original=db.meta().copy()
            with SingleOwner(db.filename.with_suffix(".lock")):
                with self.assertRaises(route.MaintenanceDenied):
                    route.commit_transition(db,proof(),owner_witness=lambda:True)
            self.assertEqual(db.meta(),original)
            db.verify()

    def test_stale_proof_revoked_owner_and_post_failure_are_atomic(self):
        with tempfile.TemporaryDirectory() as temp, closing(Database.initialize(
                Path(temp)/"fixture.sqlite",route.FROM_V33)) as db:
            db.enable(legacy_suspended=True)
            original=db.meta().copy()
            with SingleOwner(db.filename.with_suffix(".lock")),patch.object(
                    route,"build_proof",return_value=proof()):
                with self.assertRaises(route.MaintenanceDenied):
                    route.commit_transition(db,proof(),owner_witness=lambda:False)
                with self.assertRaisesRegex(route.MaintenanceDenied,"APPROVAL_OR_LEDGER_DRIFT"):
                    route.commit_transition(db,{**proof(),"history_sha256":"0"*64},
                                            owner_witness=lambda:True)
                with patch.object(db,"verify",side_effect=ValueError("post failure")):
                    with self.assertRaisesRegex(ValueError,"post failure"):
                        route.commit_transition(db,proof(),owner_witness=lambda:True)
            self.assertEqual(db.meta(),original)
            db.verify()

    def test_missing_or_unknown_contract_is_not_a_release_selector(self):
        with patch("f139.nci04_v32_original_owner_transition_cli.native_original_owner_profile") as w:
            with self.assertRaisesRegex(ValueError,"UNKNOWN_SOURCE_CONTRACT"):
                guarded_transition(None,None,None,None,None,None,_contract=object())
            w.assert_not_called()

    def test_modern_guard_requires_full_new_contract(self):
        with tempfile.TemporaryDirectory() as temp, closing(Database.initialize(
                Path(temp)/"fixture.sqlite","f"*40)) as db:
            db.enable(legacy_suspended=True)
            db.event("SOURCE_TRANSITION_ADMITTED",proof())
            with patch.object(db,"verify"),patch("f139.local_controller.g54_original_canonical"), \
                    patch("f139.nci04_g49_prepost_negative.verify_g49_custody",return_value=True), \
                    patch("f139.nci04_owner_ledger.verify_native_activation",return_value=True):
                self.assertTrue(v2_owner_terminal_release_guard("f"*40,db))
                db.event("SOURCE_TRANSITION_ADMITTED",dict(schema=route.SCHEMA,to_source_sha="f"*40))
                self.assertFalse(v2_owner_terminal_release_guard("f"*40,db))

    def test_latest_release_must_be_source_and_mechanism_bound(self):
        class Connection:
            def execute(self,*_): return self
            def fetchone(self): return {"payload":json.dumps(proof())}
        db=SimpleNamespace(conn=Connection(), verify=lambda:None)
        backend.typed_generation_custody(db,"f"*40,"1"*64)
        with self.assertRaisesRegex(backend.BackendUnavailable,"TYPED_MECHANISM_DRIFT"):
            backend.typed_generation_custody(db,"f"*40,"2"*64)

    def test_snapshot_preserves_a_grown_prefix_and_excludes_future_source_tasks(self):
        conn=sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.row_factory=sqlite3.Row
        conn.execute("CREATE TABLE events(seq INTEGER,kind TEXT,sha TEXT,payload TEXT)")
        conn.execute("CREATE TABLE tasks(ticket TEXT,stage TEXT,run_id INTEGER,evidence_sha TEXT,evidence_dir TEXT,source_sha TEXT)")
        previous=[dict(schema="forge.f139.source-transition.v28",from_source_sha="2"*40,
                       to_source_sha=route.FROM_V33)]
        from f139.nci04_negative_owner_store import TICKET as FIRST
        from f139.nci04_split_negative_owner_store import TICKET as SECOND
        from f139.nci04_g49_prepost_negative import TICKET as PREPOST
        failures=["fixture-negative-%02d"%i for i in range(29)]
        negatives=sorted([FIRST,SECOND,PREPOST,"fixture-g54"]+failures)
        for i in range(1,815):
            kind=("FREE_REASONER_ATTEMPTED" if i<=8 else
                  "MODEL_DRAFT_ATTEMPTED" if i<=65 else
                  "MODEL_DRAFT_AUTHENTICATED" if i<=122 else
                  "G3_DRAFT_ATTEMPTED" if i==123 else
                  "G3_DRAFT_AUTHENTICATED" if i==124 else "FIXTURE")
            payload="{}"
            if i==439: kind,payload="SOURCE_TRANSITION_ADMITTED",json.dumps(previous[-1])
            conn.execute("INSERT INTO events VALUES(?,?,?,?)",(i,kind,"a"*64,payload))
        for i,ticket in enumerate(["fixture-verified-%02d"%i for i in range(67)]+negatives):
            conn.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?)",(ticket,
                "QUARANTINED" if ticket in negatives else "VERIFIED",i+1,"b"*64,
                "fixture-custody",route.FROM_V33))
        db=SimpleNamespace(conn=conn,verified_native_provider_failures=lambda **_:failures)
        row=dict(seq=815,prior_sha="a"*64)
        with patch.object(route,"g54_original_canonical",return_value={"ticket":"fixture-g54"}):
            original=route.snapshot(db,row,previous)
            self.assertEqual(original["verified_historical_tasks"],67)
            self.assertEqual(original["custodied_negative_tickets"],negatives)
            conn.execute("INSERT INTO tasks VALUES('future','WAIT_PROVIDER',NULL,NULL,NULL,?)",("f"*40,))
            self.assertEqual(route.snapshot(db,row,previous),original)
            conn.execute("UPDATE tasks SET stage='WAIT_PROVIDER' WHERE ticket=?",(negatives[0],))
            with self.assertRaisesRegex(route.MaintenanceDenied,"HISTORICAL_TASK_NOT_TERMINAL"):
                route.snapshot(db,row,previous)
            conn.execute("UPDATE tasks SET stage='VERIFIED' WHERE ticket=?",(negatives[0],))
            with self.assertRaisesRegex(route.MaintenanceDenied,"ORIGINAL_TERMINAL_CUSTODY_DRIFT"):
                route.snapshot(db,row,previous)

    @unittest.skipUnless(os.name=="nt", "Windows PowerShell syntax qualification only")
    def test_installer_parses_without_executing_in_both_windows_shells(self):
        text=(ROOT/".github/workflows/f139-v34-original-owner-release.yml").read_text()
        block=text.split("        run: |\n")[1]
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"inert.ps1"
            path.write_text("\n".join(x[10:] if x.startswith(" "*10) else x
                                      for x in block.splitlines()),encoding="utf-8")
            for shell in ("powershell.exe","pwsh.exe"):
                exe=shutil.which(shell)
                self.assertIsNotNone(exe)
                cmd=("$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('"
                     +str(path).replace("'","''")+"',[ref]$t,[ref]$e);if($e.Count){$e|%{$_.Message};exit 1}")
                result=subprocess.run([exe,"-NoProfile","-NonInteractive","-Command",cmd],
                                      capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_only_one_current_release_route_and_no_schedule_or_comment(self):
        routed=[]
        for version in range(27,37):
            text=(ROOT/f".github/workflows/f139-v{version}-original-owner-release.yml").read_text()
            patterns=ast.literal_eval(re.findall(r"^    branches: (\[.*\])$",text,re.M)[0])
            if any(fnmatch.fnmatchcase("f139-owner-release-"+"f"*40,p) for p in patterns):
                routed.append(version)
        self.assertEqual(routed,[36])
        text=(ROOT/".github/workflows/f139-v35-original-owner-release.yml").read_text()
        self.assertNotIn("schedule:",text)
        self.assertNotIn("issue_comment:",text)
        self.assertEqual(text.count("$ownerLock.Lock(0,1)"),1)
        self.assertLess(text.index("$ownerLock.Lock(0,1)"),text.index("Disable-ScheduledTask"))
        self.assertLess(text.index("$ownerLock.Unlock(0,1)"),text.index("git -C $root fetch"))
        self.assertLess(text.index("ORIGINAL_COLD_CUSTODY_BUNDLE=PASS"),
                        text.index("$policyPausePossible=$true"))
        for token in ("EXACT_QUALIFICATION_REQUIRED","FINAL_LINUX_WINDOWS_RECEIPTS_REQUIRED",
                "bypass_actors","ZeroFreeBSTR($ptr)","Remove-Item Env:F139_WORKER_HMAC_KEY",
                "copy_generation_executable(db, backup.parent)",
                "POSTMUTATION_EXISTING_TASK_DISABLED_AND_QUIESCENT",
                "PRETRANSITION_POLICY_CONFLICT_HOLD"):
            self.assertIn(token,text)

    def test_both_release_jobs_use_the_same_exact_current_source_guard(self):
        text=(ROOT/".github/workflows/f139-v34-release-qualification.yml").read_text()
        baselines=re.findall(r"baseline = '([a-f0-9]{40})'",text)
        self.assertEqual(baselines,["517228adbae7e00740a74db4282d8565f7ad83ed"]*2)
        manifests=[ast.literal_eval(s) for s in re.findall(
            r"expected_paths = (\{.*?\n          \})",text,re.S)]
        self.assertEqual(len(manifests),2)
        self.assertEqual(manifests[0],manifests[1])
        self.assertEqual(len(manifests[0]),12)
        self.assertEqual(text.count("assert routed == [34]"),2)
        self.assertEqual(text.count("for version in (27, 28, 29, 30, 31, 32, 33, 34):"),2)

    @unittest.skipUnless(os.name=="nt", "real Windows byte-range interoperability only")
    def test_powershell_and_original_python_share_one_kernel_lock(self):
        ps=shutil.which("pwsh") or shutil.which("powershell")
        self.assertIsNotNone(ps)
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"original.lock"
            path.write_bytes(b"L")
            literal=str(path).replace("'","''")
            script=("$f=$null;try{$f=[IO.FileStream]::new('"+literal+"',"
                    "[IO.FileMode]::Open,[IO.FileAccess]::ReadWrite,[IO.FileShare]::ReadWrite);"
                    "$f.Lock(0,1);[Console]::Out.WriteLine('LOCKED');[Console]::Out.Flush();"
                    "[void][Console]::ReadLine();$f.Unlock(0,1);exit 0}"
                    "catch{exit 23}finally{if($f){$f.Dispose()}}")
            with SingleOwner(path):
                result=subprocess.run([ps,"-NoProfile","-NonInteractive","-Command",script],
                    input="\n",capture_output=True,text=True,timeout=20)
                self.assertEqual(result.returncode,23,result.stderr)
            child=subprocess.Popen([ps,"-NoProfile","-NonInteractive","-Command",script],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            try:
                self.assertEqual(child.stdout.readline().strip(),"LOCKED")
                with self.assertRaisesRegex(Exception,"CONTROLLER_ALREADY_RUNNING"):
                    with SingleOwner(path): pass
                out,err=child.communicate("\n",timeout=20)
                self.assertEqual(child.returncode,0,err)
            finally:
                if child.poll() is None: child.kill();child.wait(timeout=10)
            with SingleOwner(path): pass


if __name__ == "__main__":
    unittest.main()
