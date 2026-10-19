"""F124-CB exact two independently learned causal links, original 2 fixtures.

Source-neutral first-use engineering tests, not external science. No old CA,
BY, BX, BQ, BM/BN/BO/BP or original 192 TRAIN tasks/holdouts imported.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
def read(name,file):
    s=importlib.util.spec_from_file_location(name,HERE/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    return m

CB=read("F124CB_learner","f124cb_dual_link_learner.py")
SOURCE=read("F124CB_source","f124cb_frozen_engineering_source.py")


def truth(case):
    p=SOURCE.prior(case)
    return CB.pack(p["perm"],p["gains"],p["bias"],p["gates"])


class FrozenCausalBindings(unittest.TestCase):
    def test_full_domain_two_link_inverse_and_32bit_state(self):
        for case in ("CB-ENG-01","CB-ENG-02"):
            params=truth(case)
            self.assertLess(params,2**32)
            entry=SOURCE.prior(case)
            self.assertEqual(CB.unpack(params)[-1],tuple(entry["gates"]))
            for x in range(65536):
                y=CB.forward(x,params)
                self.assertEqual(CB.inverse(y,params),x)
                self.assertEqual(y,SOURCE.apply(x,entry))
                self.assertEqual(SOURCE.invert(y,entry),x)

    def test_frozen_public_FIT_learns_two_links_and_retains_one_link(self):
        for case in ("CB-ENG-01","CB-ENG-02"):
            with self.subTest(case=case):
                data,private=SOURCE.make(case)
                learned,receipt=CB.learn(data["FIT"],data["CHECK"])
                self.assertIsNotNone(learned,receipt)
                self.assertEqual(receipt["learned_flags"],
                                 tuple(SOURCE.prior(case)["gates"]))
                self.assertEqual(receipt["trained_FIT_residuals"],6560)
                self.assertEqual(receipt["trained_FIT_bit_scores"],6560)
                self.assertEqual(receipt["layout_assignments"],96)
                self.assertTrue(receipt["trained_FIT_only"])
                self.assertTrue(receipt["CHECK_veto_only"])
                self.assertFalse(receipt["source_or_graph_role_label_used"])
                self.assertFalse(receipt["science_accepted"])
                for x in (0,1,100,0x1234,0x8743,0xffff):
                    self.assertEqual(CB.forward(x,learned),
                                     SOURCE.apply(x,SOURCE.prior(case)))
                for graph,want in [(data["positive"],True),
                                   (data["hard_negative"],False)]:
                    self.assertEqual(SOURCE.truly_causal(
                        graph,SOURCE.prior(case)),want)
                self.assertFalse(private["reserved_scientific_source_used"])
                self.assertFalse(private["protected_cohort_used"])

    def test_CHECK_cannot_select_better_or_recover_from_failure(self):
        task,_=SOURCE.make("CB-ENG-02")
        state,good=CB.learn(task["FIT"],task["CHECK"])
        state_bad,bad=CB.learn(task["FIT"],
                               [(x,y^65535) for x,y in task["CHECK"]])
        self.assertIsNotNone(state)
        self.assertEqual(bad["public_FIT_sha256"],good["public_FIT_sha256"])
        self.assertEqual(bad["learned_flags"],good["learned_flags"])
        self.assertEqual(bad["FIT_bit_errors"],good["FIT_bit_errors"])
        self.assertIsNone(state_bad)
        self.assertFalse(bad["confidence"])
        self.assertGreater(bad["CHECK_bit_errors"],2)

    def test_invalid_source_state_and_public_repeats_rejected(self):
        with self.assertRaises(ValueError):
            CB.unpack(2**32)
        with self.assertRaises(ValueError):
            CB.pack((0,1,2,3),(2,1,1,1),(0,0,0,0),(1,1))
        with self.assertRaises(ValueError):
            CB.learn([(0,0)]*40,[(0,0)]*8)

if __name__=="__main__":
    unittest.main()
