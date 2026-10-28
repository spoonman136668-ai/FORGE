"""Only deterministic engineering boundary checks; no protected science."""
import unittest
import legacy30
import native6

class AC02SourceFree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy=legacy30.run()
        cls.native=native6.run()
    def test_all_original_document_claims_have_a_probe(self):
        self.assertEqual([p["id"] for p in self.legacy["probes"]],
                         ["U%02d"%n for n in range(1,31)])
        self.assertTrue(all(p["witness"] for p in self.legacy["probes"]))
        self.assertTrue(all(len(p["limitation"])>25 for p in self.legacy["probes"]))
    def test_all_six_new_ideas_have_counterexample_or_basic_probe(self):
        expected={"AC-D%d"%n for n in range(1,7)}
        self.assertEqual(set(self.native["observed_development_checks"]),expected)
        self.assertTrue(all(self.native["observed_development_checks"].values()))
    def test_hardware_claims_are_not_claimed_as_physical_experiments(self):
        cases={p["id"]:p for p in self.legacy["probes"]}
        self.assertEqual(cases["U03"]["kind"],"HARDWARE_DEPENDENCY")
        self.assertEqual(cases["U06"]["kind"],"HARDWARE_DEPENDENCY")
        self.assertFalse(self.legacy["hardware_modification"])
    def test_information_limits_are_preserved(self):
        cases={p["id"]:p for p in self.legacy["probes"]}
        for number in (9,13,17,21,22,23,26,29,30):
            self.assertEqual(cases["U%02d"%number]["kind"],"INFORMATION_LIMIT")
    def test_science_cannot_be_inferred_from_engineering_probe(self):
        self.assertFalse(self.legacy["scientific_admission"])
        self.assertFalse(self.legacy["original_first_use"])
        self.assertFalse(self.native["scientific_admission"])
        self.assertFalse(self.native["original_first_use"])
        self.assertEqual(self.legacy["result_scope"],"TOY_OR_COUNTEREXAMPLE_ONLY")
    def test_specific_negative_guardrails(self):
        self.assertIn("MISSES_INTERACTION",self.native["diagnosis"]["AC-D1"])
        self.assertIn("NO_MEMORY_SAVING",self.native["diagnosis"]["AC-D3"])
        self.assertIn("NONCAUSAL",self.native["diagnosis"]["AC-D5"])
    def test_structural_renames_are_rejected_as_unfamiliar(self):
        same=((0,"r",1),(1,"r",2),(2,"r",3))
        renamed=((3,"r",0),(0,"r",2),(2,"r",1))
        fork=((0,"r",1),(0,"r",2),(2,"r",3))
        self.assertTrue(native6.typed_isomorphic(4,same,renamed))
        self.assertFalse(native6.typed_isomorphic(4,same,fork))
        with self.assertRaises(ValueError):
            native6.typed_isomorphic(7,(),())

if __name__=="__main__":
    unittest.main()
