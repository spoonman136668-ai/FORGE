import json,pathlib,sys,unittest
HERE=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import protocol
class ReviewContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=(HERE/"frozen.json").read_bytes()
        cls.m=protocol.load(cls.raw)
    def test_exact_source_cohort_partition(self):
        x=self.m["design"]
        all_ids=sum(x["development_blocks"],[])+x["future_sealed_heldout_seeds"]
        next_task=self.m["next_prospective"]
        all_ids+=sum(next_task["dev_blocks"],[])+next_task["sealed_future"]
        self.assertEqual(len(set(all_ids)),len(all_ids))
        self.assertEqual(len(all_ids),192)
        self.assertTrue(all(v>=26000 for v in all_ids))
        self.assertEqual([c["id"] for c in self.m["candidates"]],["W36-C2","W36-C4"])
        self.assertFalse(next_task["first_use_claimed"])
    def test_prior_negative_must_be_authentic(self):
        fake={"schema":"forge.r9.independent-learned-method-development-review.v1",
              "candidate_id":"W36-C1","method_fidelity_development_verified":True,
              "all_three_folds_passed":False,"science_production_accepted":False,
              "sealed_f3_first_use_admitted":False,
              "folds":[{"fold":k,"minimum_family_gain":-0.25,"preregistered_dev_signal":False} for k in range(3)]}
        with self.assertRaisesRegex(protocol.Blocked,"SOURCE"):
            protocol.verify(self.raw,json.dumps(fake).encode())
    def test_duplicate_keys_and_nonfinite_rejected(self):
        with self.assertRaisesRegex(protocol.Blocked,"DUPLICATE"):
            protocol.load(b'{"a":1,"a":2}')
        with self.assertRaisesRegex(protocol.Blocked,"NONFINITE"):
            protocol.load(b'{"gain":NaN}')
    def test_no_unsafe_authorization_in_frozen_source(self):
        caps=self.m["limits"]
        self.assertEqual(caps["new_first_use_claims"],0)
        self.assertEqual(caps["originals_executed"],0)
        self.assertFalse(caps["science_accepted"])
        self.assertFalse(caps["external_fsa_activated"])
        self.assertFalse(caps["new_controller"])
    def test_no_stdlib_shadowing(self):
        import select as std_select
        self.assertNotEqual(std_select.__file__ if hasattr(std_select,"__file__") else "",str(HERE/"protocol.py"))
if __name__=="__main__":unittest.main()
