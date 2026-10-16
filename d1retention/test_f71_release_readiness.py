"""F71 live deployed D1 authority-denial contract, no original or migration."""
import importlib.util
import pathlib
import unittest
from unittest.mock import patch

P=pathlib.Path(__file__).with_name("f71_release_readiness.py")
spec=importlib.util.spec_from_file_location("f71_current",P)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class F71Tests(unittest.TestCase):
 def setup(self,table_objects=()):
    api=object()
    queries=[]
    names=set(table_objects)
    def select(c,db,sql):
        self.assertIs(c,api)
        self.assertEqual(db,"existing-production-db")
        self.assertTrue(sql.startswith("SELECT "))
        queries.append(sql)
        if "COUNT(*)" in sql:return [{"n":6}]
        if "sqlite_master" in sql:
            return [{"name":name,"type":
                    "table" if name=="forge_original_preuse_claims" else "trigger"}
                    for name in sorted(names)]
        self.fail("unexpected source SQL")
    return api,queries,select

 def call(self,table_objects=(),foreign=None, bookmark="a"*32, count=6,
          caps=None):
    api,queries,select=self.setup(table_objects)
    def query(c,db,sql):
        if "COUNT(*)" in sql:
            self.assertIs(c,api)
            self.assertEqual(db,"existing-production-db")
            self.assertTrue(sql.startswith("SELECT "))
            queries.append(sql)
            return [{"n":count}]
        return select(c,db,sql)
    version=caps if caps is not None else {
      "exact_single_live_version":True,
      "d1_bindings":1,
      "scientific_execution_authorized":False,
      "read_only":True,
    }
    with patch.object(m.versions,"scan",return_value=version),\
         patch.object(m.cf,"single_deployed_database",
                      return_value="existing-production-db"),\
         patch.object(m.cf,"schema_snapshot",return_value=(
             m.cf.EXPECTED_OBJECTS,
             m.witness.BASELINE_SCHEMA_SHA256 if foreign is None else foreign)),\
         patch.object(m.cf,"sql_query",side_effect=query),\
         patch.object(m.cf,"recovery_bookmark",return_value=bookmark):
        return m.inspect(api),queries

 def test_real_bound_d1_without_claim_table_cannot_release_science(self):
    d,queries=self.call()
    self.assertEqual(len(queries),3)
    self.assertTrue(d["existing_serving_worker_single_version_verified"])
    self.assertTrue(d["six_historical_originals_and_seals_preserved"])
    self.assertTrue(d["real_d1_recovery_bookmark_readable"])
    self.assertFalse(d["firstuse_schema_complete_in_actual_serving_d1"])
    self.assertFalse(d["private_restorable_backup_qualified"])
    self.assertFalse(d["real_current_scientific_owner_independently_attested"])
    self.assertFalse(d["live_complete_two_lane_original_firstuse_custody"])
    self.assertFalse(d["real_prospective_original_budget_authorized"])
    self.assertFalse(d["worker_execution_permit_issued"])
    self.assertFalse(d["production_original_claim_insert_performed"])
    self.assertEqual(d["scientific_originals_dispatched"],0)
    self.assertIn("NO_ATOMIC_FIRSTUSE_TABLE_IN_SERVING_D1",
                  d["deployment_release_blockers"])
    self.assertNotIn("recovery_bookmark",d)
    self.assertNotIn("a"*32,repr(d))
    self.assertTrue(all(s.startswith("SELECT ") for s in queries))

 def test_complete_schema_still_does_not_prove_owner_or_permit(self):
    d,queries=self.call(m.NAMES)
    self.assertTrue(d["firstuse_schema_complete_in_actual_serving_d1"])
    self.assertTrue(d["immutable_and_monotonic_trigger_names_observed"])
    self.assertFalse(d["worker_execution_permit_issued"])
    self.assertFalse(d["real_current_scientific_owner_independently_attested"])
    self.assertNotIn("NO_ATOMIC_FIRSTUSE_TABLE_IN_SERVING_D1",
                     d["deployment_release_blockers"])
    self.assertEqual(len(queries),3)

 def test_partial_schema_fails_closed_with_no_attempt_to_fix_it(self):
    for table_objects in (
      ("forge_original_preuse_claims",),
      ("forge_original_preuse_claims_insert_monotonic",),
      tuple(sorted(m.NAMES-{"forge_original_preuse_claims_update_immutable"})),
    ):
      with self.subTest(objects=table_objects),self.assertRaises(m.Blocked):
          self.call(table_objects)

 def test_current_worker_drift_or_archive_tampering_rejected(self):
    with self.assertRaises(m.Blocked):self.call(count=5)
    with self.assertRaises(m.Blocked):self.call(foreign="f"*64)
    with self.assertRaises(m.Blocked):self.call(caps={
      "exact_single_live_version":False,"d1_bindings":1,
      "scientific_execution_authorized":False,"read_only":True
    })

 def test_unavailable_recovery_bookmark_never_authorizes_release(self):
    with self.assertRaises(m.Blocked):self.call(bookmark=None)

 def test_module_contains_no_apply_restore_deploy_or_original_start(self):
    for attr in ("apply","deploy","restore","start_original","issue_permit",
                 "worker_fetch","mint_owner","grant"):
        self.assertFalse(hasattr(m,attr))
if __name__=="__main__":unittest.main()
