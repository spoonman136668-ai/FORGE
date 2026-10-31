#!/usr/bin/env python3
"""Offline G66 authenticity guard; index does not replace downloaded originals."""
import hashlib,json,pathlib,unittest,zipfile
INDEX=pathlib.Path(__file__).with_name("g66_original_zip_hash_index.json")
class G66(unittest.TestCase):
 def setUp(self):
  self.doc=json.loads(INDEX.read_text())
  self.rows={r["gate"]:r for r in self.doc["original_archives"]}
 def test_all_records(self):
  self.assertEqual(set(self.rows),{f"G{i}" for i in range(54,66)})
 def test_model_pin(self):
  self.assertEqual(self.doc["source_revision"],"607a30d783dfa663caf39e06633721c8d4cfcd7e")
  self.assertEqual(self.doc["safetensors_sha256"],"248dfc3911869ec493c76e65bf2fcf7f615828b0254c12b473182f0f81d3a707")
 def test_original_archive_identities(self):
  for r in self.rows.values():
   self.assertEqual(len(bytes.fromhex(r["zip_sha256"])),32)
 def test_unique_runs(self):
  self.assertEqual(len(set(r["run_id"] for r in self.rows.values())),12)
 def test_negative_g60(self):
  self.assertEqual(self.rows["G60"]["screen"],"FAIL")
  self.assertLess(self.rows["G60"]["representative_speedup"],1)
 def test_negative_g63_65(self):
  for g in ("G63","G64","G65"):
   self.assertEqual(self.rows[g]["screen"],"FAIL")
   self.assertLess(self.rows[g]["representative_speedup"],1)
 def test_unequal_resource_not_accepted(self):
  self.assertIn("3-vs-2",self.rows["G62"]["metric_scope"])
 def test_original_replay_preserved(self):
  self.assertEqual(self.doc["G57_embedded_receipt_gate"],"G51")
 def test_no_production(self):
  self.assertFalse(self.doc["production_eligible"])
  self.assertEqual(self.doc["scientific_acceptance"],"NOT_GRANTED")
 def test_original_byte_verification_is_separate(self):
  self.assertIn("retention",self.doc["limits"])
if __name__=="__main__":unittest.main()
