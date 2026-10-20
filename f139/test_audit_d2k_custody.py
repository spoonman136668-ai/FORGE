"""D2K-CUSTODY hosted qualification of the nonintrusive custody snapshot and fail-closed audit."""
import hashlib
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from unittest import mock
from f139.audit_d2k_custody import (
    audit, CustodyBlocked, copied_snapshot, verify_chain, REAL_23_EVENT_KINDS,
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
        # The genuine 23-event history has D2C quarantine/recovery, NOT
        # four provider-terminal events. Retain the true chronological kinds.
        with db.transaction():
            original_nine_head=None
            for i,kind in enumerate(REAL_23_EVENT_KINDS):
                if i==9:
                    original_nine_head=db.meta()["head_hash"]
                if i in (9,10):
                    original=recorded[i-9]
                    payload={
                        "ticket":original["ticket"],"run_id":original["run_id"],
                        "previous_reason":"PROVIDER_SOURCE_EVENT_SPOOFED",
                        "manifest_sha256":original["evidence_sha"],
                        "original_head_sha256":original_nine_head,
                        "original_science":False,"replay":False,
                    }
                elif i in (19,22):
                    payload=recorded[2 if i==19 else 3]
                elif i==14:
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
                    payload={"test_only":True,"iteration":i}
                db.event(kind,payload)
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

    def test_original_reconciliations_are_not_reinterpreted_as_provider_terminals(self):
        with closing(sqlite3.connect(self.dbpath)) as c:
            c.row_factory=sqlite3.Row
            entries=[dict(r) for r in c.execute("SELECT * FROM events ORDER BY seq")]
        self.assertEqual([x["kind"] for x in entries[9:11]],
            ["QUARANTINE_ORIGINAL_RECONCILED"]*2)
        self.assertEqual([entries[19]["kind"],entries[22]["kind"]],
            ["PROVIDER_VERIFIED_TERMINAL"]*2)
        proof=verify_chain(entries,self.head)
        self.assertEqual(len(proof[0]),4)
        self.assertEqual({t["ticket"] for t in proof[0].values()},set(self.provider_anchor))

    def test_repaired_quarantine_metadata_cannot_claim_original_science(self):
        with closing(sqlite3.connect(self.dbpath)) as c:
            c.row_factory=sqlite3.Row
            entries=[dict(r) for r in c.execute("SELECT * FROM events ORDER BY seq")]
        import json
        for field,new_value in (
            ("original_science",True),("replay",True),
            ("previous_reason","FORGED_ACCEPTED"),
            ("original_head_sha256","0"*64),
        ):
            with self.subTest(field=field):
                mutated=[dict(x) for x in entries]
                data=json.loads(mutated[9]["payload"])
                data[field]=new_value
                mutated[9]["payload"]=canonical(data).decode()
                # Even when an attacker recreates a locally consistent hash
                # chain and supplies that new head, the original-repair
                # semantic restrictions remain mandatory.
                prior=mutated[8]["sha"]
                for i in range(9,len(mutated)):
                    entry=mutated[i]
                    entry["prior_sha"]=prior
                    entry["sha"]=hash_bytes(canonical({
                        "seq":entry["seq"],"prior_sha":prior,
                        "kind":entry["kind"],
                        "payload":json.loads(entry["payload"]),
                    }))
                    prior=entry["sha"]
                with self.assertRaisesRegex(CustodyBlocked,
                    "D2C_ORIGINAL_RECONCILIATION_INVALID"):
                    verify_chain(mutated,prior)

    def test_mutable_d2j_manifest_drift_rejected_even_with_same_sealed_head(self):
        original_head=self.head
        original_manifest=self.provider_anchor
        with closing(sqlite3.connect(self.dbpath)) as conn, conn:
            conn.execute("UPDATE tasks SET manifest_sha=? WHERE ticket LIKE 'f139-d2j-%'",
                         ("0"*64,))
        with self.assertRaisesRegex(CustodyBlocked,"D2J_ADMISSION_TASK_BINDING_DRIFT"):
            audit(self.dbpath,SHA,self.head)
        self.assertEqual(self.head,original_head)
        self.assertIs(self.provider_anchor,original_manifest)

    def test_d2j_lane_or_source_row_drift_rejected(self):
        with closing(sqlite3.connect(self.dbpath)) as conn, conn:
            conn.execute("UPDATE tasks SET lane='Qualification' WHERE ticket LIKE 'f139-d2j-yggdrasil-%'")
        with self.assertRaisesRegex(CustodyBlocked,"D2J_ADMISSION_TASK_BINDING_DRIFT"):
            audit(self.dbpath,SHA,self.head)

    def test_wrong_sealed_head_or_source_rejected(self):
        with self.assertRaisesRegex(CustodyBlocked,"SEALED_EVENT_HEAD_MISMATCH"):
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

    def append_source_transition(self, target, *, prior_sha=None,
                                 from_source=SHA, kind="SOURCE_TRANSITION_ADMITTED",
                                 dispatches=0, originals=False):
        source=sqlite3.connect(str(self.dbpath))
        try:
            seq,previous=source.execute(
                "SELECT head_seq,head_hash FROM meta WHERE id=1").fetchone()
            payload={
                "schema":"forge.f139.source-transition.v1",
                "from_source_sha":from_source,"to_source_sha":target,
                "prior_event_head_sha256":previous if prior_sha is None else prior_sha,
                "verified_historical_tasks":4,"new_dispatches":dispatches,
                "scientific_first_use":originals,
            }
            item={"seq":seq+1,"prior_sha":previous,"kind":kind,"payload":payload}
            digest=hash_bytes(canonical(item))
            source.execute("INSERT INTO events(seq,kind,payload,prior_sha,sha) "
                           "VALUES(?,?,?,?,?)",
                           (seq+1,kind,canonical(payload).decode(),previous,digest))
            source.execute("UPDATE meta SET source_sha=?,head_seq=?,head_hash=? WHERE id=1",
                           (target,seq+1,digest))
            source.commit()
        finally:
            source.close()

    def test_exact_one_source_only_append_preserves_four_receipts(self):
        new_source="5ca118a0425dd4c6b3fa67a2f575cfda491cb8ba"
        before={(p.relative_to(self.root)).as_posix():p.read_bytes()
                for p in (self.root/"evidence").rglob("*") if p.is_file()}
        self.append_source_transition(new_source)
        with mock.patch("f139.audit_d2k_custody.D2J_SOURCE",SHA):
            proof=audit(self.dbpath,new_source,self.head)
        after={(p.relative_to(self.root)).as_posix():p.read_bytes()
               for p in (self.root/"evidence").rglob("*") if p.is_file()}
        self.assertEqual(before,after)
        self.assertEqual(proof["event_count"],24)
        self.assertEqual(proof["historical_prefix_event_count"],23)
        self.assertEqual(proof["source_only_suffix_count"],1)
        self.assertEqual(proof["archive_count"],8)
        self.assertEqual(proof["controller_actions"],0)
        self.assertNotEqual(proof["observed_current_head_sha256"],self.head)

    def test_multi_source_monotonic_merge_chain(self):
        first="99be12f448c27aea7f74a5224c9ebccf6e9d7c21"
        second="c0eaa5eef08d38417fe2875bbdd352362e130b5f"
        third="5ca118a0425dd4c6b3fa67a2f575cfda491cb8ba"
        self.append_source_transition(first)
        self.append_source_transition(second,from_source=first)
        self.append_source_transition(third,from_source=second)
        with mock.patch("f139.audit_d2k_custody.D2J_SOURCE",SHA):
            result=audit(self.dbpath,third,self.head)
        self.assertEqual(result["source_only_suffix_count"],3)
        self.assertEqual(result["event_count"],26)
        self.assertEqual(result["task_count"],4)

    def test_non_source_or_unapproved_transition_fails_closed(self):
        for config, reason in [
            ({"kind":"DEVELOPMENT_WORK_ADMITTED"},"NON_SOURCE_EVENT_AFTER_SEALED_PREFIX"),
            ({"dispatches":1},"SOURCE_SUFFIX_AUTHORITY_OR_ORDER_DRIFT"),
            ({"originals":True},"SOURCE_SUFFIX_AUTHORITY_OR_ORDER_DRIFT"),
            ({"prior_sha":"0"*64},"SOURCE_SUFFIX_AUTHORITY_OR_ORDER_DRIFT"),
            ({"from_source":"0"*40},"SOURCE_SUFFIX_AUTHORITY_OR_ORDER_DRIFT"),
            ({"target":"e"*40},"SOURCE_SUFFIX_AUTHORITY_OR_ORDER_DRIFT"),
        ]:
            with self.subTest(config=config):
                # Reset to exact source and sealed prefix: subcases are isolated.
                with tempfile.TemporaryDirectory() as scratch:
                    replacement=Path(scratch)/"source.sqlite"
                    original=sqlite3.connect(self.dbpath)
                    copy=sqlite3.connect(replacement)
                    try: original.backup(copy)
                    finally: copy.close();original.close()
                    current=self.dbpath
                    self.dbpath=replacement
                    try:
                        arguments=dict(config)
                        target=arguments.pop("target",
                           "5ca118a0425dd4c6b3fa67a2f575cfda491cb8ba")
                        self.append_source_transition(target,**arguments)
                        with mock.patch("f139.audit_d2k_custody.D2J_SOURCE",SHA):
                            with self.assertRaisesRegex(CustodyBlocked,reason):
                                audit(self.dbpath,target,self.head)
                    finally:
                        self.dbpath=current

    def test_earlier_history_cannot_be_resealed_using_new_head(self):
        target="5ca118a0425dd4c6b3fa67a2f575cfda491cb8ba"
        self.append_source_transition(target)
        new=sqlite3.connect(str(self.dbpath))
        try:
            current_head=new.execute(
                "SELECT head_hash FROM meta WHERE id=1").fetchone()[0]
        finally: new.close()
        with mock.patch("f139.audit_d2k_custody.D2J_SOURCE",SHA):
            with self.assertRaisesRegex(CustodyBlocked,"SEALED_EVENT_HEAD_MISMATCH"):
                audit(self.dbpath,target,current_head)

    def test_integrated_suffix_and_mutable_task_manifest_drift(self):
        target="365e5eb8b888c11716376973ad2551523a869bab"
        self.append_source_transition(target)
        with mock.patch("f139.audit_d2k_custody.D2J_SOURCE",SHA):
            record=audit(self.dbpath,target,self.head)
        self.assertEqual(record["source_only_suffix_count"],1)
        self.assertEqual(record["d2j_task_bindings_verified"],2)
        self.assertEqual(record["task_count"],4)
        with closing(sqlite3.connect(self.dbpath)) as conn, conn:
            conn.execute("UPDATE tasks SET manifest_sha=? WHERE ticket LIKE 'f139-d2j-%'",("0"*64,))
        with mock.patch("f139.audit_d2k_custody.D2J_SOURCE",SHA):
            with self.assertRaisesRegex(CustodyBlocked,"D2J_ADMISSION_TASK_BINDING_DRIFT"):
                audit(self.dbpath,target,self.head)

    def test_integrated_unpinned_event_head_never_accepted(self):
        target="365e5eb8b888c11716376973ad2551523a869bab"
        self.append_source_transition(target)
        with mock.patch("f139.audit_d2k_custody.D2J_SOURCE",SHA):
            with self.assertRaisesRegex(CustodyBlocked,"SEALED_EVENT_HEAD_MISMATCH"):
                audit(self.dbpath,target,"0"*64)

    def test_monotonic_jump_to_latest_qualified_main(self):
        first="e8166b1ef2f52ad935029ee583a5a0827b8a25d8"
        final="365e5eb8b888c11716376973ad2551523a869bab"
        self.append_source_transition(first)
        self.append_source_transition(final,from_source=first)
        with mock.patch("f139.audit_d2k_custody.D2J_SOURCE",SHA):
            record=audit(self.dbpath,final,self.head)
        self.assertEqual(record["source_only_suffix_count"],2)
        self.assertEqual(record["event_count"],25)
        self.assertEqual(record["d2j_task_bindings_verified"],2)

    def test_absent_sealed_authority_fails_closed(self):
        with self.assertRaisesRegex(CustodyBlocked,"EXPECTED_PREFIX_NOT_SUPPLIED"):
            audit(self.dbpath,SHA,"")
        with self.assertRaisesRegex(CustodyBlocked,"EXPECTED_SOURCE_INVALID"):
            audit(self.dbpath,"unexpected",self.head)


if __name__=="__main__":
    unittest.main()
