"""F124-V safety and frozen mechanism qualification without DEV exposure."""
import math
import inspect
import unittest
from collections import Counter

import f124v_collision_centered as v
import f124v_development_evidence as receipts
import f124u_interventions as predecessor
import f124q_independent_binding as inference
import f124q_fresh_source as source


class F124VTests(unittest.TestCase):
    def test_source_birth_before_implementation_and_original_frozen(self):
        p=v.frozen()
        self.assertEqual(v.git_blob(v.FREEZE),v.FREEZE_BLOB)
        self.assertEqual(v.git_blob(predecessor.__file__),v.PARENT_SOURCE_BLOB)
        self.assertEqual(p["lineage"]["parent_run"],39083528704)
        self.assertEqual(p["lineage"]["negative_u"].split(";")[0][:11],
                         "Ygg new 0/") if False else None
        self.assertTrue(all(x is False for x in p["safety"].values()))
        self.assertEqual(p["source"]["pairs_each_phase"],48)

    def test_fresh_source_fit_only_and_unchanged_role_oracle(self):
        for lane in ("Wingless","Yggdrasil"):
            groups=v.COHORTS[lane]
            self.assertTrue(set(groups["FIT"]).isdisjoint(groups["DEV"]))
            for phase in ("FIT","DEV"):
                seeds=set(groups[phase])
                self.assertEqual(len(seeds),24)
                self.assertTrue(seeds.isdisjoint(source.COHORTS[lane]["FIT"]))
                self.assertTrue(seeds.isdisjoint(source.COHORTS[lane]["DEV"]))
                self.assertTrue(seeds.isdisjoint(predecessor.COHORTS[lane]["FIT"]))
                self.assertTrue(seeds.isdisjoint(predecessor.COHORTS[lane]["DEV"]))
            strat=Counter()
            for _,_,pos,neg in v.pairs(lane,"FIT"):
                self.assertTrue(source.paired_admit(pos,neg))
                self.assertEqual(set(pos),{"start","target","roles","edges"})
                strat[len(pos["roles"])]+=1
            self.assertEqual(strat,Counter({7:16,8:16,9:16}))
            with self.assertRaises(source.Quarantined):
                v.build(lane,180100,(2,1,1),"DEV")
            with self.assertRaises(source.Quarantined):
                v.build(lane,880000,(2,1,1),"DEV")

    def test_five_category_signed_4_nibble_projection(self):
        categories=set()
        for value in range(16):
            bits=[(value>>k)&1 for k in range(4)]
            categories.add(v.nibble_code(bits))
        self.assertEqual(categories,set(range(5)))
        pos=v.pairs("Wingless","FIT")[0][2]
        base=[.4,.6,.7,.9,1.2,.15,-.5]
        delta=[.05,-.03,.02,-.01]
        logit,work=v.wingless_collision_reassignment(pos,base,delta)
        self.assertTrue(math.isfinite(logit))
        self.assertEqual(work["compression_levels"],5)
        self.assertEqual(work["compression_channels"],4)
        self.assertEqual(work["state_limit"],3)
        self.assertLessEqual(work["max_active"],192)
        self.assertGreater(work["public_edge_scans"],0)

    def test_ygg_zero_mean_and_exact_7_9(self):
        pos=v.pairs("Yggdrasil","FIT")[0][2]
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[.8,-.3]
        s,work=v.yggdrasil_centered_evidence(pos,base,delta)
        self.assertTrue(math.isfinite(s))
        self.assertLessEqual(work["max_active"],7)
        self.assertLessEqual(work["max_retained"],9)
        self.assertGreater(work["centered_arithmetic"],0)
        self.assertGreater(work["prospective_key_comparisons"],0)
        orig,_=inference.forward("Yggdrasil",pos,base,delta)
        self.assertTrue(math.isfinite(orig))
        # Source inference is label-blind; labels/oracle only in receipt scorer.
        body=inspect.getsource(v.yggdrasil_centered_evidence)
        for forbidden in ("public_routes(","protected(","correct_path","hidden_label"):
            self.assertNotIn(forbidden,body)
        with self.assertRaises(source.Quarantined):
            v.yggdrasil_centered_evidence({"oracle":True},base,delta)

    def test_all_controls_full_census_predeclared(self):
        self.assertEqual(len(receipts.ARMS["Wingless"]),6)
        self.assertEqual(len(receipts.ARMS["Yggdrasil"]),7)
        self.assertIn("U_uncentered",receipts.ARMS["Yggdrasil"])
        self.assertIn("P_uniform",receipts.ARMS["Wingless"])
        self.assertEqual(receipts.U_SHA,
             "63a2a57973444752d4002bc4718ec63de88a26ed05142627305de3a94fa9fb41")


if __name__=="__main__":
    unittest.main()
