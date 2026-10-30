"""H5 handoff evidence boundary and new-lane regression tests."""
import json
import unittest
from pathlib import Path

from validate_registry import Invalid
from validate_handoff import validate_handoff

RAW = (Path(__file__).resolve().parent / "handoff.v1.json").read_bytes()

class HandoffTests(unittest.TestCase):
    def change(self, mutate):
        x=json.loads(RAW)
        mutate(x)
        return json.dumps(x).encode()

    def test_inventory_is_source_pointer_only(self):
        x=validate_handoff(RAW)
        self.assertTrue(x["handoff_index_valid"])
        self.assertFalse(x["retirement_ready"])
        self.assertGreaterEqual(x["workstreams"],9)

    def test_no_chat_retirement_self_certification(self):
        with self.assertRaises(Invalid):
            validate_handoff(self.change(lambda x: x.__setitem__("chat_retirement_ready",True)))
        with self.assertRaises(Invalid):
            validate_handoff(self.change(lambda x: x.__setitem__("inventory_completeness","PASS")))

    def test_no_execution_authority(self):
        with self.assertRaises(Invalid):
            validate_handoff(self.change(lambda x: x.__setitem__("execution_authorized",True)))

    def test_scientific_lineage_is_not_combined(self):
        with self.assertRaises(Invalid):
            validate_handoff(self.change(lambda x: x["workstreams"][0].__setitem__("separate_scientific_lineage",False)))
        with self.assertRaises(Invalid):
            validate_handoff(self.change(lambda x: x["workstreams"][1].__setitem__("oversight","forge-operations")))

    def test_new_research_approach_is_advisory_only(self):
        def extend(x):
            extra=json.loads(json.dumps(x["workstreams"][2]))
            extra["id"]="new-causal-proposal"
            x["workstreams"].append(extra)
        self.assertEqual(validate_handoff(self.change(extend))["workstreams"],12)

    def test_no_accepted_new_source_owner_without_qualification(self):
        with self.assertRaises(Invalid):
            validate_handoff(self.change(lambda x: x["workstreams"][2]["source_pointers"][0].__setitem__("claim","ACCEPTED")))

    def test_no_duplicate_workstream(self):
        with self.assertRaises(Invalid):
            validate_handoff(self.change(lambda x: x["workstreams"].append(x["workstreams"][0].copy())))

    def test_no_loss_of_native_intelligence(self):
        with self.assertRaises(Invalid):
            validate_handoff(self.change(lambda x: x["workstreams"].pop(0)))

    def test_no_fake_source_or_sha(self):
        for k,v in (("url","file:///local/ledger"),("sha","not-a-commit")):
            with self.subTest(k=k),self.assertRaises(Invalid):
                validate_handoff(self.change(lambda x: x["workstreams"][0]["source_pointers"][0].__setitem__(k,v)))

    def test_no_duplicate_json_root_keys(self):
        with self.assertRaises(Invalid):
            validate_handoff(RAW[:-2]+b', "Advisory_Only": true }')

    def test_no_missing_owner_witness(self):
        with self.assertRaises(Invalid):
            validate_handoff(self.change(lambda x: x["workstreams"][-1].__setitem__("source_pointers",[])))

    def test_bio_optimizer_language_are_three_separate_scientific_scopes(self):
        h=json.loads(RAW)
        required={"bio-research","optimizer-research","language-research"}
        self.assertTrue(required.issubset({w["id"] for w in h["workstreams"]}))
        self.assertEqual(len(h["workstreams"]), 11)
        self.assertNotIn("bio-optimizer-language",{w["id"] for w in h["workstreams"]})
        for w in h["workstreams"]:
            if w["id"] in required:
                self.assertTrue(w["separate_scientific_lineage"])
                self.assertEqual(w["handoff_status"], "UNVERIFIED")
                self.assertEqual(w["oversight"], "unified-research")
                self.assertEqual(w["source_pointers"], [])

    def test_denies_loss_of_any_support_science_lane(self):
        for ident in ("bio-research","optimizer-research","language-research"):
            with self.subTest(ident=ident),self.assertRaises(Invalid):
                validate_handoff(self.change(lambda x: x["workstreams"].__setitem__(
                    slice(None),[row for row in x["workstreams"] if row["id"]!=ident])))

    def test_denies_grouping_support_science_as_one(self):
        def combine(x):
            x["workstreams"]=[w for w in x["workstreams"] if w["id"] not in
                ("bio-research","optimizer-research","language-research")]
            extra=dict(x["workstreams"][2])
            extra["id"]="bio-optimizer-language"
            x["workstreams"].append(extra)
        with self.assertRaises(Invalid):
            validate_handoff(self.change(combine))

if __name__=="__main__":
    unittest.main()
