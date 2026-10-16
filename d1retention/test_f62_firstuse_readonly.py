"""F62: non-authorizing local migration qualification + remote-read fault injection."""
import importlib.util
import pathlib
import tempfile
import unittest
from unittest.mock import patch

HERE=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location("f62_preflight", HERE/"f62_firstuse_readonly.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class F62Tests(unittest.TestCase):
    def test_exact_additive_source_and_sqlite_replay_guards(self):
        statements,digest=m.migration_sql()
        self.assertEqual(len(statements),4)
        self.assertEqual(len(digest),64)
        self.assertEqual(statements[0].count("CREATE TABLE"),1)
        self.assertEqual(sum("CREATE TRIGGER" in stmt for stmt in statements),3)

    def test_live_observation_reads_only_and_never_approves(self):
        api=object()
        queries=[]
        def dbread(a, db, q):
            self.assertIs(a,api)
            self.assertEqual(db,"known-deployed-d1")
            self.assertTrue(q.startswith("SELECT "))
            queries.append(q)
            if "SELECT COUNT(*)" in q:return [{"n":6}]
            if "sqlite_master" in q:return []
            self.fail("unexpected SQL")
        with patch.object(m.cf,"single_deployed_database",return_value="known-deployed-d1") as db,             patch.object(m.cf,"schema_snapshot",return_value=(m.ORIGINALS,m.witness.BASELINE_SCHEMA_SHA256)) as schema,             patch.object(m.cf,"sql_query",side_effect=dbread),             patch.object(m.cf,"recovery_bookmark",return_value="1a2b3c4d-"*5) as backup:
            result=m.audit(api)
        db.assert_called_once_with(api)
        schema.assert_called_once_with(api,"known-deployed-d1")
        backup.assert_called_once_with(api,"known-deployed-d1")
        self.assertEqual(len(queries),3)
        self.assertEqual(result["disposition"],"BLOCKED_OWNER_CUSTODY_AND_D1_MIGRATION_NOT_DEPLOYED")
        self.assertTrue(result["d1_time_travel_bookmark_readable"])
        self.assertTrue(result["six_previous_original_archives_and_seals_unchanged"])
        self.assertFalse(result["real_atomic_preuse_table_deployed"])
        self.assertFalse(result["private_verified_backup_created"])
        self.assertFalse(result["worker_permit_issued"])
        self.assertFalse(result["scientific_execution_authorized"])
        self.assertFalse(result["owner_cutover_authorized"])
        self.assertNotIn("recovery_bookmark",result)

    def test_unavailable_or_changed_authoritative_live_state_blocks(self):
        cases=[
            ("schema",{"schema":(set(),m.witness.BASELINE_SCHEMA_SHA256)}),
            ("foreign",{"schema":(m.ORIGINALS,"f"*64)}),
            ("counts",{"count":5}),
            ("new claim table",{"existing":[{"name":"forge_original_preuse_claims","type":"table"}]}),
            ("missing bookmark",{"bookmark":None}),
        ]
        for name,overrides in cases:
            with self.subTest(name=name):
                def reads(a,db,q):
                    if "COUNT(*)" in q:return [{"n":overrides.get("count",6)}]
                    return overrides.get("existing",[])
                with patch.object(m.cf,"single_deployed_database",return_value="real"),                     patch.object(m.cf,"schema_snapshot",return_value=overrides.get(
                         "schema",(m.ORIGINALS,m.witness.BASELINE_SCHEMA_SHA256))),                     patch.object(m.cf,"sql_query",side_effect=reads),                     patch.object(m.cf,"recovery_bookmark",return_value=overrides.get(
                         "bookmark","a"*32)):
                    with self.assertRaises((m.Denied,m.cf.InstallBlocked)):
                        m.audit(object())

    def test_rewrite_or_missing_migration_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            candidate=pathlib.Path(d)/"unsafe.sql"
            candidate.write_text("DROP TABLE forge_research_originals;\n")
            with patch.object(m,"R35",candidate):
                with self.assertRaises(m.Denied):
                    m.migration_sql()
            candidate.unlink()
            with patch.object(m,"R38",candidate):
                with self.assertRaises(m.Denied):
                    m.migration_sql()

    def test_unauthorized_retry_or_remote_side_effects_not_exposed(self):
        self.assertFalse(hasattr(m,"apply"))
        self.assertFalse(hasattr(m,"install"))
        self.assertFalse(hasattr(m,"dispatch"))
        self.assertFalse(hasattr(m,"restore"))
        self.assertFalse(hasattr(m,"worker_permit"))
if __name__=="__main__": unittest.main()
