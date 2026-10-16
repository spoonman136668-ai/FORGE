"""F63 local durability, crash and cross-lane no-replay qualification.

NO live D1 connection, Worker, original experiment or scientific authority.
"""
import concurrent.futures
import dataclasses
import pathlib
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import f63_local_oneuse as m

def candidate(key="a"*64,lane="Wingless",sequence=100,epoch=7):
    return m.Candidate(key,lane,epoch,"b"*40,"c"*64,"d"*64,sequence)

def pins(c):
    return m.FrozenLocalTestPins(**{
        field:getattr(c,field) for field in m.FrozenLocalTestPins.__dataclass_fields__
    })

class F63Tests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path=pathlib.Path(self.dir.name)/"one-use-local-only.db"
        self.db=sqlite3.connect(self.path,timeout=20,isolation_level=None)
        self.addCleanup(self.db.close)
        self.db.execute("CREATE TABLE original_archives "
                        "(archive_id INTEGER PRIMARY KEY, retained TEXT NOT NULL)")
        for i in range(1,7):
            self.db.execute("INSERT INTO original_archives VALUES (?,?)",(i,"sealed"))
        self.original_schema=self.db.execute(
            "SELECT sql FROM sqlite_master WHERE name='original_archives'").fetchone()[0]
        self.digest=m.install_isolated_test_schema(self.db)

    def inspect(self, c):
        return m.inspect_local_consumption(self.db,c.original_key_sha256)

    def test_real_sqlite_file_consumption_does_not_create_permit(self):
        c=candidate()
        report=m.local_attempt_once(self.db,c,pins(c))
        self.assertTrue(report["sandbox_intent_irrevocably_consumed"])
        self.assertFalse(report["external_cloudflare_firstuse_consumed"])
        self.assertFalse(report["worker_scope_permit_issued"])
        self.assertFalse(report["real_scientific_execution_authorized"])
        self.assertFalse(report["owner_cutover_authorized"])
        self.assertEqual(report["originals_dispatched"],0)
        self.assertEqual(self.inspect(c)[0][-1],0)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM original_archives").fetchone()[0],6)
        self.assertEqual(self.original_schema,self.db.execute(
            "SELECT sql FROM sqlite_master WHERE name='original_archives'").fetchone()[0])

    def test_crash_after_commit_then_restart_cannot_retry(self):
        c=candidate()
        first=m.local_attempt_once(self.db,c,pins(c))
        self.assertTrue(first["sandbox_intent_irrevocably_consumed"])
        # A real worker can terminate after commit and before response:
        # reconstruct a completely fresh connection to the durable DB.
        self.db.close()
        self.db=sqlite3.connect(self.path,timeout=20,isolation_level=None)
        with self.assertRaises(m.Denied):
            m.local_attempt_once(self.db,c,pins(c))
        self.assertEqual(len(self.inspect(c)),1)
        self.assertEqual(self.inspect(c)[0][-1],0)

    def test_lost_acknowledgement_is_consume_not_replay(self):
        c=candidate()
        m.local_attempt_once(self.db,c,pins(c))
        # Failure after persisted claim is always uncertain from caller view;
        # repeat is denied, not treated as a new start.
        try:
            raise ConnectionError("simulated transport acknowledgement lost")
        except ConnectionError:
            with self.assertRaises(m.Denied):
                m.local_attempt_once(self.db,c,pins(c))
        self.assertEqual(len(self.inspect(c)),1)

    def test_twenty_four_competing_workers_one_consume(self):
        c=candidate()
        def attempt(_):
            db=sqlite3.connect(self.path,timeout=30,isolation_level=None)
            try:
                try:
                    result=m.local_attempt_once(db,c,pins(c))
                    return result["sandbox_intent_irrevocably_consumed"]
                except m.Denied:
                    return False
            finally:
                db.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results=list(pool.map(attempt,range(24)))
        self.assertEqual(sum(results),1)
        self.assertEqual(len(self.inspect(c)),1)

    def test_monotonic_cross_lane_sequence_and_epoch(self):
        c=candidate()
        m.local_attempt_once(self.db,c,pins(c))
        # A different lane with the same sequence is not a new right to run.
        for bad in (
            candidate("e"*64,"Yggdrasil",100,7),
            candidate("e"*64,"Yggdrasil",99,7),
            candidate("e"*64,"Yggdrasil",101,6),
            candidate("a"*64,"Wingless",105,8),
        ):
            with self.subTest(candidate=bad):
                with self.assertRaises(m.Denied):
                    m.local_attempt_once(self.db,bad,pins(bad))
        follow=candidate("f"*64,"Yggdrasil",101,8)
        r=m.local_attempt_once(self.db,follow,pins(follow))
        self.assertFalse(r["worker_scope_permit_issued"])
        self.assertEqual(len(self.inspect(follow)),1)
        self.assertEqual(self.db.execute(
            "SELECT claimed_sequence FROM forge_original_preuse_claims "
            "ORDER BY claimed_sequence").fetchall(),[(100,),(101,)])

    def test_independently_pinned_source_identity_cannot_drift(self):
        c=candidate()
        bads=[
            dataclasses.replace(c,original_key_sha256="a"*63),
            dataclasses.replace(c,source_commit_sha="F"*40),
            dataclasses.replace(c,claimed_sequence=0),
            dataclasses.replace(c,owner_epoch=0),
            dataclasses.replace(c,scientific_authorized=True),
            dataclasses.replace(c,lane="FORGE"),
            dataclasses.replace(c,claimed_sequence=True),
        ]
        for bad in bads:
            with self.subTest(bad=bad):
                with self.assertRaises(m.Denied):
                    m.local_attempt_once(self.db,bad,pins(c))
        with self.assertRaises(m.Denied):
            m.local_attempt_once(self.db,c,dataclasses.replace(
                pins(c),source_commit_sha="f"*40))
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM forge_original_preuse_claims").fetchone()[0],0)

    def test_failure_before_insert_is_always_blocked(self):
        c=candidate()
        self.db.execute("DROP TRIGGER forge_original_preuse_claims_insert_monotonic")
        # Never consume even a sandbox claim when monotonic guard is gone.
        with self.assertRaises(m.Denied):
            m.local_attempt_once(self.db,c,pins(c))
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM forge_original_preuse_claims").fetchone()[0],0)

    def test_missing_local_schema_and_uncertain_sql_commit_fail(self):
        other=sqlite3.connect(":memory:",isolation_level=None)
        self.addCleanup(other.close)
        c=candidate()
        with self.assertRaises(m.Denied):
            m.local_attempt_once(other,c,pins(c))
        self.assertFalse(hasattr(m,"deploy"))
        self.assertFalse(hasattr(m,"worker_fetch"))
        self.assertFalse(hasattr(m,"dispatch"))
        self.assertFalse(hasattr(m,"authorize_science"))
        self.assertFalse(hasattr(m,"cloudflare_api"))

    def test_reinstall_or_preexisting_table_never_runs(self):
        with self.assertRaises(m.Denied):
            m.install_isolated_test_schema(self.db)

if __name__=="__main__":
    unittest.main()
