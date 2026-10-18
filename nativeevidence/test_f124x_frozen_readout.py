"""F124-X source/fixed controls and readout-only parity tests (FIT only)."""
import math
import unittest
from collections import Counter

import f124x_frozen_models as x
import f124x_development_evidence as evidence
import f124w_hop_trace_indexed as w
import f124v_collision_centered as old
import f124q_fresh_source as source


class F124XTests(unittest.TestCase):
    def test_freeze_authentic_model_and_fixed_hypotheses(self):
        p=x.frozen()
        self.assertEqual(w.blob(x.FREEZE),x.FREEZE_BLOB)
        self.assertEqual(w.blob(w.__file__),x.W_BLOB)
        self.assertEqual(p["lineage"]["parent_actions_run"],39085219061)
        self.assertEqual(p["Wingless"]["selected_checksum"],list(x.SELECTED))
        self.assertFalse(p["control"]["scientific_acceptance"])
        self.assertFalse(p["control"]["matched_compute_superiority"])
        self.assertFalse(p["control"]["merge"])

    def test_FIT_source_birth_balanced_and_disjoint(self):
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(x.COHORTS[lane]["FIT"]).isdisjoint(
                            x.COHORTS[lane]["DEV"]))
            self.assertTrue(set(x.COHORTS[lane]["FIT"]).isdisjoint(
                            w.COHORTS[lane]["FIT"]))
            counts=Counter()
            for _,_,positive,negative in x.pairs(lane,"FIT"):
                self.assertTrue(source.paired_admit(positive,negative))
                counts[len(positive["roles"])]+=1
            self.assertEqual(counts,Counter({7:16,8:16,9:16}))
            with self.assertRaises(source.Quarantined):
                x.build(lane,880000,(2,1,1),"FIT")

    def test_new_FIT_primary_index_preserves_exact_old_outputs(self):
        base=[.7,.6,.9,.5,.8,.12,-.55]
        delta=[.1,-.03,.07,-.02]
        for _,_,pos,neg in x.pairs("Wingless","FIT")[:5]:
            for graph in (pos,neg):
                a,_=w.indexed_wingless(graph,base,delta,w.PRIMARY)
                b,_=old.wingless_collision_reassignment(graph,base,delta)
                self.assertEqual(a,b)
                c,work=w.indexed_wingless(graph,base,delta,x.SELECTED)
                self.assertTrue(math.isfinite(c))
                self.assertLessEqual(work["max_active"],192)
                self.assertEqual(work["compression_levels"],5)
                self.assertGreater(work["max_encoded_entries"],0)

    def test_ygg_only_readout_divisor_changes_no_path(self):
        base=[.4,.9,.65,.75,.8,.2,-.5]
        delta=[1.3,.2]
        for _,_,pos,neg in x.pairs("Yggdrasil","FIT")[:3]:
            for g in (pos,neg):
                a,wa,ta=x.frozen_yggdrasil_score(g,base,delta,"V_centered")
                b,wb,tb=x.frozen_yggdrasil_score(g,base,delta,"V_depth_minus_one")
                control,wcontrol=old.yggdrasil_centered_evidence(g,base,delta)
                self.assertEqual(a,control)
                self.assertEqual(wa,wcontrol)
                self.assertEqual(wa,wb)
                self.assertEqual(ta,tb)
                depth=len(g["roles"])
                active=ta[-1]["active"]+ta[-1]["retained"]
                best=max((entry[2] for entry in active if entry[0]==g["target"]),
                         default=-2.*depth)
                self.assertEqual(b,4.*(best/max(1,depth-1)-base[6]))
                self.assertLessEqual(len(ta[-1]["active"]),7)
                self.assertLessEqual(len(ta[-1]["retained"]),9)

    def test_no_oracle_in_model_and_frozen_comparators(self):
        import inspect
        for routine in (x.build,x.frozen_yggdrasil_score):
            body=inspect.getsource(routine)
            self.assertNotIn("public_routes(",body)
            self.assertNotIn("exact_reference_path(",body)
            self.assertNotIn("protected(",body)
        self.assertEqual(len(evidence.WING_ARMS),4)
        self.assertEqual(len(evidence.YGG_ARMS),4)
        self.assertEqual(evidence.W_RAW_SHA,
            "122c0f1db5547a1ce2074c73c0b4b4d089c7f00eaf4573327676be3b7b521698")


if __name__=="__main__":
    unittest.main()
