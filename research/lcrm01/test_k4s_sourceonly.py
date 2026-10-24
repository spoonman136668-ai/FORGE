"""K4S original-source and scientific-claim boundary tests (never MiniGrid eval)."""
import json
import tempfile
import unittest
from pathlib import Path
from k4s_native_interface_gate import FROZEN,git_blob,canonical,SCHEMA

class K4SReadOnlyGuards(unittest.TestCase):
    def test_frozen_public_source_and_original_hashes(self):
        p=json.loads(FROZEN.read_text())
        self.assertEqual(p["schema"],"mass.lcrm01.k4s.frozen-native-policy-interface-evidence-gate.v1")
        self.assertEqual(p["public_benchmark"]["legal_navigation_actions"],[0,1,2])
        self.assertEqual(p["parent"]["K4R_original_artifact_id"],12561177548)
        self.assertEqual(len(p["parent"]["K4R_members_sha256"]),3)
    def test_originals_are_cross_repository_distinct(self):
        p=json.loads(FROZEN.read_text())
        repos={x["repo"] for x in p["independent_native_candidates"]}
        self.assertEqual(repos,{"spoonman136668-ai/Wingless","spoonman136668-ai/Yggdrasil"})
        self.assertEqual(len({x["blob"] for x in p["independent_native_candidates"]}),3)
        self.assertTrue(all(len(x["commit"])==40 for x in p["independent_native_candidates"]))
    def test_no_automatic_policy_authorization(self):
        p=json.loads(FROZEN.read_text())
        self.assertTrue(p["governance"]["no_unfrozen_heldout_episode"])
        self.assertFalse(p["governance"]["scientific_accepted"])
        self.assertFalse(p["governance"]["scientific_first_use"])
        self.assertTrue(p["governance"]["do_not_modify_native_repos"])
    def test_git_source_blob_is_content_addressed(self):
        raw=b"public native code"
        import hashlib
        self.assertEqual(git_blob(raw),hashlib.sha1(b"blob 18\0"+raw).hexdigest())
    def test_binary_is_not_triaction(self):
        public={0,1,2}
        for candidate in json.loads(FROZEN.read_text())["independent_native_candidates"][:2]:
            self.assertFalse(public.issubset(set(candidate["supported_actions"])))
    def test_receipt_schema_requires_unaccepted_science(self):
        self.assertTrue(SCHEMA.endswith("native-policy-source-admission-v1"))
        self.assertIn("a",canonical({"a":1}))

if __name__=="__main__":
    unittest.main()
