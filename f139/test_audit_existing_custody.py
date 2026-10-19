"""D2L hosted qualification of the nonintrusive custody snapshot and fail-closed audit."""
import hashlib
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from f139.audit_existing_custody import audit, CustodyBlocked, copied_snapshot
from f139.local_controller import Database, canonical, hash_bytes, store_evidence
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
        for i,(ticket,lane) in enumerate(items,1):
            task={"ticket":ticket,"lane":lane,"source_sha":SHA}
            archives={label:artifact(task,i,label)
                      for label in ("ubuntu-latest","windows-latest")}
            folder,digest=store_evidence(self.root,ticket,i,archives)
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
                payload=(recorded[terminal_indexes.index(i)]
                         if i in terminal_indexes else {"test_only":True,"iteration":i})
                db.event("PROVIDER_VERIFIED_TERMINAL" if i in terminal_indexes
                         else kind,payload)
        self.head=db.meta()["head_hash"]
        db.close()

    def test_exact_sealed_23_event_chain_eight_archives_no_original_writes(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        result=audit(self.dbpath,SHA,self.head)
        after={p.name:p.read_bytes() for p in self.root.iterdir() if p.is_file()}
        self.assertEqual(before,after)
        self.assertEqual(result["event_count"],23)
        self.assertEqual(result["task_count"],4)
        self.assertEqual(result["archive_count"],8)
        self.assertEqual(result["controller_actions"],0)
        self.assertEqual(result["original_database_writes"],0)

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

    def test_absent_sealed_authority_fails_closed(self):
        with self.assertRaisesRegex(CustodyBlocked,"EXPECTED_PREFIX_NOT_SUPPLIED"):
            audit(self.dbpath,SHA,"")
        with self.assertRaisesRegex(CustodyBlocked,"EXPECTED_SOURCE_INVALID"):
            audit(self.dbpath,"unexpected",self.head)


if __name__=="__main__":
    unittest.main()
