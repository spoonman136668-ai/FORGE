"""D2K-CUSTODY hosted qualification of the nonintrusive custody snapshot and fail-closed audit."""
import hashlib
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from unittest import mock
from f139.audit_d2k_custody import (
    audit, CustodyBlocked, copied_snapshot,
    load_provider_anchor as real_load_provider_anchor,
)
from f139.local_controller import Database, canonical, hash_bytes, store_evidence, d2j_plan
from test_local_controller import SHA, artifact


class ReadonlyCustodyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="f139-d2l-tests-")
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.dbpath=self.root/"state.sqlite"
        db=Database.initialize(self.dbpath,SHA)
        # Synthetic activated snapshot: no native scheduler or controller is started.
        db.conn.execute("UPDATE meta SET enabled=1,legacy_suspended=1 WHERE id=1")
        items=[
            ("f139-d2c-qualification-659bb1f4d751","Qualification"),
            ("f139-d2c-wingless-659bb1f4d751","Wingless"),
            ("f139-d2j-wingless-"+SHA[:12],"Wingless"),
            ("f139-d2j-yggdrasil-"+SHA[:12],"Yggdrasil")]
        recorded=[]
        self.provider_anchor={}
        for i,(ticket,lane) in enumerate(items,1):
            task={"ticket":ticket,"lane":lane,"source_sha":SHA}
            archives={label:artifact(task,i,label)
                      for label in ("ubuntu-latest","windows-latest")}
            folder,digest=store_evidence(self.root,ticket,i,archives)
            self.provider_anchor[ticket]={
                "ticket":ticket,"run_id":i,"source_sha":SHA,
                "artifacts":{label:{
                    "artifact_id":i*100+(1 if label=="ubuntu-latest" else 2),
                    "sha256":hash_bytes(raw),"size_in_bytes":len(raw)}
                    for label,raw in archives.items()}}
            db.conn.execute(
                "INSERT INTO tasks(ticket,lane,source_sha,stage,manifest_sha,"
                "run_id,evidence_dir,evidence_sha) VALUES(?,?,?,'VERIFIED',?,?,?,?)",
                (ticket,lane,SHA,"f"*64,i,folder,digest))
            recorded.append({"ticket":ticket,"run_id":i,"evidence_sha":digest})
        kinds=["SYNTHETIC_EVENT"]*23
        for index in (2,5,9): kinds[index]="SOURCE_TRANSITION_ADMITTED"
        kinds[14]="UNATTENDED_SUCCESSION_ADMITTED"
        terminal_indexes=(0,3,17,20)
        with db.transaction():
            for i,kind in enumerate(kinds):
                if i==14:
                    plan=d2j_plan(SHA,db.meta()["head_hash"])
                    manifest_sha256=hash_bytes(canonical(plan))
                    for task in plan["tasks"]:
                        db.conn.execute("UPDATE tasks SET manifest_sha=? WHERE ticket=?",
                            (manifest_sha256,task["ticket"]))
                    payload={"schema":plan["schema"],"source_sha":SHA,
                             "prior_event_head_sha256":db.meta()["head_hash"],
                             "manifest_sha256":manifest_sha256,
                             "tickets":[task["ticket"] for task in plan["tasks"]],
                             "new_dispatches":0,"scientific_first_use":False}
                else:
                    payload=(recorded[terminal_indexes.index(i)]
                             if i in terminal_indexes else {"test_only":True,"iteration":i})
                db.event("PROVIDER_VERIFIED_TERMINAL" if i in terminal_indexes
                         else kind,payload)
        self.head=db.meta()["head_hash"]
        db.close()
        patcher=mock.patch("f139.audit_d2k_custody.load_provider_anchor",
                          return_value=self.provider_anchor)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_exact_sealed_23_event_chain_eight_archives_no_original_writes(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        result=audit(self.dbpath,SHA,self.head)
        after={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        self.assertEqual(before,after)
        self.assertEqual(result["event_count"],23)
        self.assertEqual(result["task_count"],4)
        self.assertEqual(result["archive_count"],8)
        self.assertEqual(result["external_provider_anchor_records"],4)
        self.assertEqual(result["external_provider_artifacts_checked"],8)
        self.assertEqual(result["d2j_task_bindings_verified"],2)
        self.assertEqual(result["controller_actions"],0)
        self.assertEqual(result["original_database_writes"],0)

    def test_mutable_d2j_manifest_drift_rejected_even_with_same_sealed_head(self):
        original_head=self.head
        original_manifest=self.provider_anchor
        with sqlite3.connect(self.dbpath) as conn:
            conn.execute("UPDATE tasks SET manifest_sha=? WHERE ticket LIKE 'f139-d2j-%'",
                         ("0"*64,))
        with self.assertRaisesRegex(CustodyBlocked,"D2J_ADMISSION_TASK_BINDING_DRIFT"):
            audit(self.dbpath,SHA,self.head)
        self.assertEqual(self.head,original_head)
        self.assertIs(self.provider_anchor,original_manifest)

    def test_d2j_lane_or_source_row_drift_rejected(self):
        with sqlite3.connect(self.dbpath) as conn:
            conn.execute("UPDATE tasks SET lane='Qualification' WHERE ticket LIKE 'f139-d2j-yggdrasil-%'")
        with self.assertRaisesRegex(CustodyBlocked,"D2J_ADMISSION_TASK_BINDING_DRIFT"):
            audit(self.dbpath,SHA,self.head)

    def test_wrong_sealed_head_or_source_rejected(self):
        with self.assertRaisesRegex(CustodyBlocked,"SEALED_METADATA_NOT_MATCHED"):
            audit(self.dbpath,SHA,"0"*64)
        with self.assertRaisesRegex(CustodyBlocked,"SEALED_METADATA_NOT_MATCHED"):
            audit(self.dbpath,"0"*40,self.head)

    def test_tampered_archive_cannot_self_certify(self):
        p=next((self.root/"evidence").rglob("windows-latest.zip"))
        p.write_bytes(p.read_bytes()+b"tampered")
        with self.assertRaisesRegex(CustodyBlocked,"ARCHIVE_SHA_CHANGED"):
            audit(self.dbpath,SHA,self.head)

    def test_modified_database_snapshot_detected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"state.sqlite"
            p.write_bytes(b"first")
            dest=Path(td)/"scratch";dest.mkdir()
            from unittest import mock
            real=Path.read_bytes
            count=[0]
            def changed(self):
                if self==p:
                    count[0]+=1
                    return b"first" if count[0]==1 else b"second"
                return real(self)
            with mock.patch.object(Path,"read_bytes",changed):
                with self.assertRaisesRegex(CustodyBlocked,"DATABASE_CHANGED_DURING_COPY"):
                    copied_snapshot(p,dest)

    def test_exact_real_provider_manifest_has_four_source_pinned_runs(self):
        anchor=real_load_provider_anchor()
        self.assertEqual(set(anchor),{
            "f139-d2c-qualification-659bb1f4d751",
            "f139-d2c-wingless-659bb1f4d751",
            "f139-d2j-wingless-4a5665d9d01b",
            "f139-d2j-yggdrasil-4a5665d9d01b"})
        self.assertEqual(len([x for r in anchor.values()
                              for x in r["artifacts"].values()]),8)

    def test_locally_rehashed_archive_rejected_by_independent_provider_anchor(self):
        ticket="f139-d2j-wingless-"+SHA[:12]
        local=self.provider_anchor[ticket]["artifacts"]["windows-latest"]
        local["sha256"]="a"*64
        with self.assertRaisesRegex(CustodyBlocked,"EXTERNAL_PROVIDER_ARTIFACT_DRIFT"):
            audit(self.dbpath,SHA,self.head)

    def test_provider_run_and_source_drift_rejected(self):
        ticket="f139-d2j-yggdrasil-"+SHA[:12]
        self.provider_anchor[ticket]["run_id"]=293
        with self.assertRaisesRegex(CustodyBlocked,"EXTERNAL_PROVIDER_RUN_OR_SOURCE_DRIFT"):
            audit(self.dbpath,SHA,self.head)

    def test_absent_sealed_authority_fails_closed(self):
        with self.assertRaisesRegex(CustodyBlocked,"EXPECTED_PREFIX_NOT_SUPPLIED"):
            audit(self.dbpath,SHA,"")
        with self.assertRaisesRegex(CustodyBlocked,"EXPECTED_SOURCE_INVALID"):
            audit(self.dbpath,"unexpected",self.head)


if __name__=="__main__":
    unittest.main()
