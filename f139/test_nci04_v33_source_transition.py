"""V33 contract falsification. Synthetic fixtures grant no original authority."""
from contextlib import closing
import fnmatch
import ast
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
from unittest.mock import Mock,patch

from f139 import nci04_v33_source_transition as route
from f139.local_controller import Database,SingleOwner,v2_owner_terminal_release_guard,v17_original_model_history_valid
from f139.nci04_native_contract import digest
from f139.nci04_v32_original_owner_transition_cli import copy_generation_executable,guarded_transition
from f139 import nci04_genenv_owner_backend as backend
ROOT=Path(__file__).resolve().parents[1]


def proof():
    return dict(schema=route.SCHEMA,from_source_sha=route.FROM_V32,to_source_sha="f"*40,
        owner_event_id=41500000000,prior_event_head_sha256=route.ORIGINAL_HEAD,
        verified_historical_tasks=34,custodied_negative_tasks=21,
        custodied_negative_tickets=["negative-%d"%i for i in range(21)],
        terminal_tasks_sha256="a"*64,history_sha256="b"*64,v32_transition_sha256="c"*64,
        genenv_executable_sha256="d"*64,genenv_toolchain=route.TOOLCHAIN,
        generation_mechanism_sha256="e"*64,new_dispatches=0,
        scientific_first_use=False,v2_receipt_authorized=False)


class V33Tests(unittest.TestCase):
    def test_missing_genuine_history_cannot_mutate_source(self):
        with tempfile.TemporaryDirectory() as temp,closing(Database.initialize(
                Path(temp)/"fixture.sqlite",route.FROM_V32)) as db:
            db.enable(legacy_suspended=True)
            original=db.meta().copy()
            with SingleOwner(db.filename.with_suffix(".lock")):
                with self.assertRaises(route.MaintenanceDenied):
                    route.commit_transition(db,proof(),owner_witness=lambda:True)
            self.assertEqual(db.meta(),original)
            db.verify()

    def test_exact_cold_seal_rejects_source_binary_mechanism_replay_and_authority_drift(self):
        doc=proof()
        state={k:doc[k] for k in ("verified_historical_tasks","custodied_negative_tasks",
            "custodied_negative_tickets","terminal_tasks_sha256","history_sha256","v32_transition_sha256")}
        previous=[dict(schema="forge.f139.source-transition.v27",from_source_sha="a"*40,
                       to_source_sha=route.FROM_V32)]
        row=dict(seq=439,prior_sha=route.ORIGINAL_HEAD)
        with patch.object(route,"snapshot",return_value=state):
            route.verify_cold_event(None,row,doc,previous)
            for changes in (dict(generation_mechanism_sha256="unbound"),dict(genenv_executable_sha256="bad"),
                    dict(genenv_toolchain="go1.24"),dict(history_sha256="f"*64),
                    dict(scientific_first_use=True),dict(v2_receipt_authorized=True),
                    dict(new_dispatches=1),dict(to_source_sha=route.FROM_V32),
                    dict(owner_event_id=True),dict(extra="denied")):
                with self.subTest(changes=changes),self.assertRaises(route.MaintenanceDenied):
                    route.verify_cold_event(None,row,{**doc,**changes},previous)
            with self.assertRaises(route.MaintenanceDenied):
                route.verify_cold_event(None,row,doc,previous+[doc])
            with self.assertRaises(route.MaintenanceDenied):
                route.verify_cold_event(None,{**row,"seq":438},doc,previous)

    def test_failed_post_verify_rolls_back_and_revoked_owner_cannot_commit(self):
        with tempfile.TemporaryDirectory() as temp,closing(Database.initialize(
                Path(temp)/"fixture.sqlite",route.FROM_V32)) as db:
            db.enable(legacy_suspended=True)
            before=db.meta().copy()
            with SingleOwner(db.filename.with_suffix(".lock")),patch.object(
                    route,"build_proof",return_value=proof()):
                with self.assertRaises(route.MaintenanceDenied):
                    route.commit_transition(db,proof(),owner_witness=lambda:False)
                with self.assertRaisesRegex(route.MaintenanceDenied,"APPROVAL_OR_LEDGER_DRIFT"):
                    route.commit_transition(db,{**proof(),"generation_mechanism_sha256":"f"*64},
                                            owner_witness=lambda:True)
                with patch.object(db,"verify",side_effect=ValueError("post-transition failure")):
                    with self.assertRaisesRegex(ValueError,"post-transition failure"):
                        route.commit_transition(db,proof(),owner_witness=lambda:True)
            self.assertEqual(db.meta(),before)
            db.verify()

    def test_complete_new_schema_is_required_by_modern_guard(self):
        with tempfile.TemporaryDirectory() as temp,closing(Database.initialize(
                Path(temp)/"fixture.sqlite","f"*40)) as db:
            db.enable(legacy_suspended=True)
            db.event("SOURCE_TRANSITION_ADMITTED",proof())
            with patch.object(db,"verify"),patch("f139.local_controller.g54_original_canonical"), \
                    patch("f139.nci04_g49_prepost_negative.verify_g49_custody",return_value=True), \
                    patch("f139.nci04_owner_ledger.verify_native_activation",return_value=True):
                self.assertTrue(v2_owner_terminal_release_guard("f"*40,db))
                db.event("SOURCE_TRANSITION_ADMITTED",dict(schema=route.SCHEMA,
                    to_source_sha="f"*40,v2_receipt_authorized=False))
                self.assertFalse(v2_owner_terminal_release_guard("f"*40,db))
                db.event("SOURCE_TRANSITION_ADMITTED",{**proof(),"schema":"forge.f139.source-transition.v29"})
                self.assertFalse(v2_owner_terminal_release_guard("f"*40,db))

    def test_model_free_drafts_do_not_reset_or_expand_inference_budget(self):
        counters=dict(G3_DRAFT_ATTEMPTED=1,G3_DRAFT_AUTHENTICATED=1,
            MODEL_DRAFT_ATTEMPTED=11,MODEL_DRAFT_AUTHENTICATED=11,FREE_REASONER_ATTEMPTED=8)
        self.assertTrue(route.preserved_counters_valid(counters))
        self.assertFalse(v17_original_model_history_valid(counters))
        for key,value in (("FREE_REASONER_ATTEMPTED",9),("MODEL_DRAFT_ATTEMPTED",12),
                          ("MODEL_DRAFT_AUTHENTICATED",10),("G3_DRAFT_ATTEMPTED",True)):
            self.assertFalse(route.preserved_counters_valid({**counters,key:value}))
        self.assertFalse(route.preserved_counters_valid({**counters,"unknown":0}))

    def test_prior_executable_backup_hash_is_independent_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            binary=root/"original.exe"
            binary.write_bytes(b"fixture-only")
            original=binary.read_bytes()
            expected=digest(original)
            db=SimpleNamespace(meta=lambda:dict(source_sha=route.FROM_V32))
            backup=root/"backup"
            backup.mkdir()
            with patch.object(backend,"executable_custody",return_value=(binary,expected)):
                copied=copy_generation_executable(db,backup)
                self.assertEqual(copy_generation_executable(db,backup,copy_files=False),copied)
                target=backup/next(iter(copied))
                target.write_bytes(b"tamper")
                with self.assertRaisesRegex(ValueError,"PRIOR_GENERATOR_BACKUP_HASH"):
                    copy_generation_executable(db,backup,copy_files=False)
            self.assertEqual(binary.read_bytes(),original)

    def test_typed_custody_and_contract_selection_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp,closing(Database.initialize(
                Path(temp)/"fixture.sqlite",route.FROM_V32)) as db:
            with self.assertRaisesRegex(backend.BackendUnavailable,"TYPED_RELEASE_NOT_BOUND"):
                backend.typed_generation_custody(db,route.FROM_V32,"a"*64)
        with patch("f139.nci04_v32_original_owner_transition_cli.native_original_owner_profile") as witness:
            with self.assertRaisesRegex(ValueError,"UNKNOWN_SOURCE_CONTRACT"):
                guarded_transition(None,None,None,None,None,None,_contract=object())
            witness.assert_not_called()

    def test_only_current_installer_receives_new_release_pushes(self):
        routed=[]
        for version in range(27,37):
            text=(ROOT/f".github/workflows/f139-v{version}-original-owner-release.yml").read_text()
            patterns=ast.literal_eval(re.findall(r"^    branches: (\[.*\])$",text,re.M)[0])
            if any(fnmatch.fnmatchcase("f139-owner-release-"+"f"*40,p) for p in patterns):
                routed.append(version)
        self.assertEqual(routed,[36])
        text=(ROOT/".github/workflows/f139-v33-original-owner-release.yml").read_text()
        for token in ("EXACT_QUALIFICATION_REQUIRED","FINAL_LINUX_WINDOWS_RECEIPTS_REQUIRED",
                "bypass_actors","ZeroFreeBSTR($ptr)","Remove-Item Env:F139_WORKER_HMAC_KEY",
                "preserved_counters_valid","copy_generation_executable(db, backup.parent)",
                "POSTMUTATION_EXISTING_TASK_DISABLED_AND_QUIESCENT"):
            self.assertIn(token,text)
        self.assertNotIn("issue_comment:",text)
        self.assertNotIn("schedule:",text)


    def test_snapshot_retains_every_terminal_negative_and_exact_spent_prefix(self):
        conn=sqlite3.connect(":memory:")
        self.addCleanup(conn.close)
        conn.row_factory=sqlite3.Row
        conn.execute("CREATE TABLE events(seq INTEGER,kind TEXT,sha TEXT,payload TEXT)")
        conn.execute("CREATE TABLE tasks(ticket TEXT,stage TEXT,run_id INTEGER,evidence_sha TEXT,evidence_dir TEXT,source_sha TEXT)")
        previous=[dict(schema="forge.f139.source-transition.v27",from_source_sha="a"*40,to_source_sha=route.FROM_V32)]
        from f139.nci04_negative_owner_store import TICKET as FIRST
        from f139.nci04_split_negative_owner_store import TICKET as SECOND
        from f139.nci04_g49_prepost_negative import TICKET as PREPOST
        failures=["fixture-negative-%02d"%i for i in range(17)]
        negatives=sorted([FIRST,SECOND,PREPOST,"fixture-g54"]+failures)
        for i in range(1,439):
            kind=("FREE_REASONER_ATTEMPTED" if i<=8 else
                  "MODEL_DRAFT_ATTEMPTED" if i<=19 else
                  "MODEL_DRAFT_AUTHENTICATED" if i<=30 else "FIXTURE")
            payload="{}"
            if i==400:
                kind="SOURCE_TRANSITION_ADMITTED"
                payload=json.dumps(previous[-1])
            conn.execute("INSERT INTO events VALUES(?,?,?,?)",(i,kind,
                route.ORIGINAL_HEAD if i==438 else "a"*64,payload))
        for i,ticket in enumerate(["fixture-verified-%02d"%i for i in range(34)]+negatives):
            conn.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?)",(ticket,
                "QUARANTINED" if ticket in negatives else "VERIFIED",i+1,"b"*64,
                "fixture-custody",route.FROM_V32))
        db=SimpleNamespace(conn=conn,verified_native_provider_failures=lambda **_:failures)
        row=dict(seq=439,prior_sha=route.ORIGINAL_HEAD)
        with patch.object(route,"g54_original_canonical",return_value={"ticket":"fixture-g54"}):
            result=route.snapshot(db,row,previous)
            self.assertEqual(result["verified_historical_tasks"],34)
            self.assertEqual(result["custodied_negative_tickets"],negatives)
            conn.execute("UPDATE tasks SET stage='ACTIVE' WHERE ticket=?",(negatives[0],))
            with self.assertRaisesRegex(route.MaintenanceDenied,"HISTORICAL_TASK_NOT_TERMINAL"):
                route.snapshot(db,row,previous)
            conn.execute("UPDATE tasks SET stage='VERIFIED' WHERE ticket=?",(negatives[0],))
            with self.assertRaisesRegex(route.MaintenanceDenied,"ORIGINAL_TERMINAL_CUSTODY_DRIFT"):
                route.snapshot(db,row,previous)
            conn.execute("UPDATE tasks SET stage='QUARANTINED' WHERE ticket=?",(negatives[0],))
            conn.execute("UPDATE events SET kind='FIXTURE' WHERE seq=1")
            with self.assertRaisesRegex(route.MaintenanceDenied,"SPENT_HISTORY_DRIFT"):
                route.snapshot(db,row,previous)


    def test_policy_transport_fallback_is_bounded_read_only_and_fail_closed(self):
        text=(ROOT/".github/workflows/f139-v33-original-owner-release.yml").read_text()
        start=text.index("          function Read-V33OwnerPolicy {")
        end=text.index("          $policy=Read-V33OwnerPolicy",start)
        function="\n".join(line[10:] for line in text[start:end].splitlines())
        self.assertLess(end,text.index("Disable-ScheduledTask -TaskName $name"))
        self.assertEqual(function.count("gh api repos/"),1)
        self.assertEqual(function.count("Invoke-RestMethod -Method Get"),1)
        for denied in ("-Method Post","-Method Patch","-Method Put",
                       "Start-ScheduledTask","Stop-ScheduledTask","Disable-ScheduledTask",
                       "Start-Sleep","while(","for(","F139_WORKER_HMAC_KEY"):
            self.assertNotIn(denied,function)
        self.assertIn("-MaximumRedirection 0 -TimeoutSec 30",function)
        # No stale native exit code may reject a successful independent GET.
        guard=text[end:text.index("$release=",end)]
        self.assertNotIn("$LASTEXITCODE",guard)
        for check in ("$policy.state -cne 'open'","$policy.user.login -cne 'spoonman136668-ai'",
                      "$ownerPolicy.enabled -ne $false","$ownerPolicy.source_sha -cne $old",
                      "$ownerPolicy.scientific_first_use -ne $false"):
            self.assertIn(check,guard)
        if os.name!="nt":
            self.skipTest("Windows PowerShell behavioral fallback fixture")
        executable=shutil.which("powershell.exe")
        self.assertIsNotNone(executable)
        fixture=r"""
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$env:GH_TOKEN='fixture-only-never-a-credential'
$script:mode='primary'
$script:primary=0
$script:fallback=0
function gh {
    $script:primary++
    if($script:mode -eq 'primary') {
        $global:LASTEXITCODE=0
        return '{"marker":"primary"}'
    }
    if($script:mode -eq 'malformed') {
        $global:LASTEXITCODE=0
        return '{malformed'
    }
    $global:LASTEXITCODE=1
    return ''
}
function Invoke-RestMethod {
    param($Method,$MaximumRedirection,$TimeoutSec,$ErrorAction,$Uri,$Headers)
    $script:fallback++
    if($Method -cne 'Get' -or $MaximumRedirection -ne 0 -or $TimeoutSec -ne 30 -or
       $Uri -cne 'https://api.github.com/repos/spoonman136668-ai/FORGE/issues/807' -or
       $Headers.Authorization -cne 'Bearer fixture-only-never-a-credential' -or
       $Headers.Accept -cne 'application/vnd.github+json' -or
       $Headers['X-GitHub-Api-Version'] -cne '2022-11-28') {throw 'fixture transport drift'}
    if($script:mode -eq 'both-fail'){throw 'fixture transport unavailable'}
    return [pscustomobject]@{marker='fallback'}
}
"""
        assertions=r"""
$result=Read-V33OwnerPolicy
if($result.marker -cne 'primary' -or $script:primary -ne 1 -or $script:fallback -ne 0) {
    throw 'primary fixture failed'
}
$script:mode='fallback'
$result=Read-V33OwnerPolicy
if($result.marker -cne 'fallback' -or $script:primary -ne 2 -or $script:fallback -ne 1) {
    throw 'independent fallback fixture failed'
}
$script:mode='both-fail'
$denied=$false
try {Read-V33OwnerPolicy | Out-Null} catch {
    $denied=($_.Exception.Message -ceq 'F139_V33_POLICY_READ_UNAVAILABLE_NO_OWNER_MUTATION')
}
if(-not $denied -or $script:primary -ne 3 -or $script:fallback -ne 2) {
    throw 'both failures must deny without another request'
}
$script:mode='malformed'
$denied=$false
try {Read-V33OwnerPolicy | Out-Null} catch {$denied=$true}
if(-not $denied -or $script:primary -ne 4 -or $script:fallback -ne 2) {
    throw 'malformed successful response must deny without fallback'
}
Remove-Item Env:GH_TOKEN
Write-Host 'F139_V33_POLICY_TRANSPORT_FIXTURE=PASS'
"""
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"read-only-policy-fixture.ps1"
            path.write_text(fixture+"\n"+function+"\n"+assertions,encoding="utf-8")
            result=subprocess.run([executable,"-NoProfile","-NonInteractive","-File",str(path)],
                                  capture_output=True,check=False)
            self.assertEqual(result.returncode,0,result.stdout.decode(errors="replace")+
                             result.stderr.decode(errors="replace"))
            self.assertIn(b"F139_V33_POLICY_TRANSPORT_FIXTURE=PASS",result.stdout)

    def test_windows_powershell_inert_parse(self):
        if os.name!="nt":
            self.skipTest("Windows PowerShell parser")
        executable=shutil.which("powershell.exe")
        self.assertIsNotNone(executable)
        text=(ROOT/".github/workflows/f139-v33-original-owner-release.yml").read_text()
        for block in text.split("        run: |\n")[1:]:
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/"inert-parse.ps1"
                path.write_text("\n".join(x[10:] if x.startswith(" "*10) else x
                                          for x in block.splitlines()),encoding="utf-8")
                result=subprocess.run([executable,"-NoProfile","-NonInteractive","-Command",
                    "$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('"
                    +str(path).replace("'","''")+"',[ref]$t,[ref]$e);if($e.Count){$e|%{$_.Message};exit 1}"],
                    capture_output=True,check=False)
                self.assertEqual(result.returncode,0,result.stdout.decode(errors="replace"))


if __name__=="__main__":
    unittest.main()
