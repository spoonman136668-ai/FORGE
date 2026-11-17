"""Frozen V53 successor replay and negative controls, no live owner access."""
from __future__ import annotations
import copy
import json
import unittest
import inspect

from f139 import nci04_v53_owner_forward_repair_cli as cli
from f139 import nci04_v41_cold_copy_verifier as cold

from f139.nci04_native_contract import canonical, digest
from f139.nci04_v53_owner_forward_repair import (
    FIELDS, FROM_SOURCE, HEAD_SEQ, HEAD_SHA, MIN_OWNER_COMMENT,
    PURPOSE, READONLY_RUN, SCHEMA,
    ForwardRepairDenied, verify_cold_event,
)

PREVIOUS_TRANSITION_SHA = 'c' * 64  # fixture-only validated predecessor hash

class Result:
    def __init__(self, row):
        self.row = row
    def fetchone(self):
        return self.row

class Conn:
    def __init__(self, tasks):
        self.tasks = tasks
        self.anchor = {
            "seq": HEAD_SEQ,
            "kind": "NATIVE_DEVELOPMENT_ACTIVATED",
            "sha": HEAD_SHA,
            "prior_sha": PREVIOUS_TRANSITION_SHA,
            "payload": json.dumps({
                "schema": "forge.f139.nci04.owner-native-activation.v1",
                "source_sha": FROM_SOURCE, "development_only": True,
                "scientific_first_use": False, "new_dispatches": 0,
            }),
        }
    def execute(self, sql, *args):
        if sql.startswith("SELECT seq,kind,sha,prior_sha,payload FROM events"):
            return Result(self.anchor)
        if sql.startswith("SELECT ticket,lane,source_sha,stage"):
            return iter(self.tasks)
        raise AssertionError("unqualified query: " + sql[:70])

class DB:
    def __init__(self, tasks):
        self.conn = Conn(tasks)

def test_case():
    history = []
    for i in range(153):
        history.append({
            "ticket": "p" + str(i).zfill(4),
            "lane": "Wingless" if i % 2 else "Yggdrasil",
            "source_sha": FROM_SOURCE,
            "stage": "VERIFIED", "manifest_sha": "a"*64,
            "run_id": i+1, "evidence_dir": "/sealed",
            "evidence_sha": "b"*64, "quarantine_reason": None,
        })
    for i in range(56):
        history.append({
            "ticket": "q" + str(i).zfill(4),
            "lane": "Wingless", "source_sha": FROM_SOURCE,
            "stage": "QUARANTINED", "manifest_sha": "a"*64,
            "run_id": None, "evidence_dir": None,
            "evidence_sha": None, "quarantine_reason": "sealed",
        })
    history.sort(key=lambda x: x["ticket"])
    digest_history = digest(canonical(history))
    tickets = sorted(x["ticket"] for x in history
                     if x["stage"] == "QUARANTINED")
    prev = [{
        "schema": "forge.f139.source-transition.v42",
        "from_source_sha": "4ccbb84785a43e038453d6f2bda5415ecb364084",
        "to_source_sha": FROM_SOURCE,
        "verified_historical_tasks": 153,
        "custodied_negative_tasks": 56,
        "custodied_negative_tickets": tickets,
        "terminal_tasks_sha256": digest_history,
    }]
    doc = {
        "schema": SCHEMA,
        "from_source_sha": FROM_SOURCE, "to_source_sha": "a"*40,
        "prior_event_head_sha256": HEAD_SHA,
        "original_activation_sha256": HEAD_SHA,
        "previous_source_transition_sha256": PREVIOUS_TRANSITION_SHA,
        "owner_comment_id": MIN_OWNER_COMMENT+1,
        "qualified_main_run_id": 43996137366,
        "rehearsal_run_id": 43996174295,
        "original_readonly_run_id": READONLY_RUN,
        "backup_sqlite_sha256": "b"*64,
        "terminal_tasks_sha256": digest_history,
        "custodied_negative_tickets": tickets,
        "verified_historical_tasks": 153,
        "custodied_negative_tasks": 56,
        "source_repair_purpose": PURPOSE,
        "new_dispatches": 0, "scientific_first_use": False,
        "native_development_approved": True,
        "new_controller": False, "new_scheduler": False,
        "new_queue": False, "paid_api_calls": 0,
    }
    row = {"seq": HEAD_SEQ+1, "prior_sha": HEAD_SHA}
    return DB(history), row, doc, prev

class V53Replay(unittest.TestCase):
    def test_frozen_replay_and_exact_fields(self):
        db,row,doc,prev = test_case()
        self.assertEqual(set(doc), FIELDS)
        self.assertTrue(verify_cold_event(db,row,doc,prev))

    def test_mutated_source_rejected(self):
        db,row,doc,prev=test_case()
        for key,value in (
            ("from_source_sha","c"*40),
            ("to_source_sha",FROM_SOURCE),
            ("to_source_sha","4ccbb84785a43e038453d6f2bda5415ecb364084"),
            ("prior_event_head_sha256","f"*64),
            ("original_activation_sha256","f"*64),
            ("original_readonly_run_id",0),
            ("native_development_approved",False),
            ("scientific_first_use",True),
            ("new_dispatches",1),
            ("new_queue",True),
            ("paid_api_calls",1),
            ("backup_sqlite_sha256","a"),
            ("terminal_tasks_sha256","f"*64),
            ("owner_comment_id",MIN_OWNER_COMMENT),
            ("custodied_negative_tasks",55),
            ("rehearsal_run_id",doc["qualified_main_run_id"]),
        ):
            corrupted=dict(doc)
            corrupted[key]=value
            with self.subTest(key=key,value=value):
                with self.assertRaises(ForwardRepairDenied):
                    verify_cold_event(db,row,corrupted,prev)

    def test_replay_and_old_activation_tampering_rejected(self):
        db,row,doc,prev=test_case()
        badprev=prev+[dict(prev[0],schema=SCHEMA)]
        with self.assertRaises(ForwardRepairDenied):
            verify_cold_event(db,row,doc,badprev)
        db.conn.anchor["sha"]="f"*64
        with self.assertRaises(ForwardRepairDenied):
            verify_cold_event(db,row,doc,prev)

    def test_historical_task_mutations_rejected(self):
        db,row,doc,prev=test_case()
        db.conn.tasks[4]["stage"]="QUARANTINED"
        with self.assertRaises(ForwardRepairDenied):
            verify_cold_event(db,row,doc,prev)

    def test_live_staging_only_accepts_exact_source_and_reproducible_binary(self):
        # Static negative-control coverage for owner-only PowerShell: these
        # checks are NOT a substitute for original Windows-owner rehearsal.
        from pathlib import Path
        script = (Path(__file__).resolve().parent /
                  "v53_original_owner_repair.ps1").read_text(encoding="utf-8")
        self.assertNotIn("SOURCE_CANDIDATE_ALREADY_STAGED", script)
        self.assertIn("(GitSource $stage) -ceq $Main", script)
        self.assertIn("EXISTING_STAGE_SOURCE_NOT_EXACT", script)
        self.assertIn("EXISTING_STAGE_IGNORED_OR_UNTRACKED", script)
        self.assertIn("EXISTING_BINARY_DIR_INVALID", script)
        self.assertIn("EXISTING_BINARY_BYTES_NOT_REPRODUCIBLE", script)
        self.assertIn("Get-FileHash -LiteralPath $buildBinary -Algorithm SHA256", script)
        self.assertIn("SOURCE_BINARY_TEMP_COLLISION", script)
        self.assertIn("ORPHAN_BINARY_WITHOUT_SOURCE", script)
        self.assertIn("Move-Item -LiteralPath $buildBinary -Destination $binary", script)
        self.assertNotIn("Remove-Item -LiteralPath $stage", script)
        self.assertNotIn("Remove-Item -LiteralPath $binaryDir", script)
        self.assertLess(script.index("EXISTING_BINARY_BYTES_NOT_REPRODUCIBLE"),
                        script.index("Disable-ScheduledTask -TaskName $name"))

    def test_detached_copy_preserves_exact_adjacent_negative_custody(self):
        # A standalone SQLite backup lacks the two historically consumed ZIPs;
        # verify V53 reuses the already-qualified hash-bound copy primitive.
        source = inspect.getsource(cli.backed_up)
        self.assertIn("source.parent.resolve() != copy_path.parent.resolve()", source)
        self.assertIn("cold.required_negative_custody(verified_source)", source)
        self.assertIn("cold.copy_negative_custody(", source)
        self.assertIn("copy_files=not adjunct.exists()", source)
        self.assertIn("DETACHED_NEGATIVE_CUSTODY_SYMLINK", source)
        self.assertIn("read_frozen(copy_path)", source)
        self.assertIn("read_frozen(source)", source)
        self.assertNotIn("symlink_to(", source)
        helper = inspect.getsource(cold.copy_negative_custody)
        self.assertIn("digest(payload) == wanted", helper)
        self.assertIn('destination.open("xb")', helper)

if __name__ == "__main__":
    unittest.main()
