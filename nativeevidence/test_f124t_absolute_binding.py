"""F124-T frozen new-hypothesis and no-first-use source checks."""
import inspect
import math
import unittest

import f124t_absolute_binding as t
import f124s_anchored_surrogate as s
import f124q_independent_binding as q
import f124t_development_evidence as evidence
import f124q_fresh_source as source


class TestF124T(unittest.TestCase):
    def test_preimplementation_source_and_nonretune(self):
        p=t.frozen()
        self.assertEqual(t.git_blob(t.FREEZE),t.FREEZE_BLOB)
        self.assertEqual(p["lineage"]["failed_f124s_head"],
                         "ca0326d5b957647d7131dc1f043c2d9765d466e4")
        self.assertFalse(p["lineage"]["failed_f124s_DEV_built"])
        self.assertTrue(p["training"]["no_restart_or_retune_on_failure"])
        self.assertTrue(all(v is False for v in p["authority"].values()))

    def test_stale_cohorts_and_protected_denied(self):
        for lane in ("Wingless","Yggdrasil"):
            self.assertTrue(set(t.COHORTS[lane]["FIT"]).isdisjoint(
                            set(s.COHORTS[lane]["FIT"]) |
                            set(s.COHORTS[lane]["DEV"])))
            self.assertTrue(set(t.COHORTS[lane]["DEV"]).isdisjoint(
                            set(t.COHORTS[lane]["FIT"]) |
                            set(s.COHORTS[lane]["DEV"])))
            counts={7:0,8:0,9:0}
            for graphpos,graphneg in t.pairs(lane,"FIT"):
                self.assertTrue(source.paired_admit(graphpos,graphneg))
                counts[len(graphpos["roles"])]+=1
            self.assertEqual(counts,{7:16,8:16,9:16})
            with self.assertRaises(source.Quarantined):
                t.build(lane,180100,[2,1,1],"DEV")

    def test_observed_old_fraction_flat_and_new_absolute_sensitive(self):
        base=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
        pos,neg=t.build("Yggdrasil",690000,t.VECTORS[0],"FIT")
        frozen_old,_=s.smooth_yggdrasil(pos,base,[0.,0.])
        perturbed_old,_=s.smooth_yggdrasil(pos,base,[0.08,-0.08])
        self.assertAlmostEqual(frozen_old,perturbed_old,places=12)
        a,work=t.absolute_yggdrasil(pos,base,[0.,0.])
        b,_=t.absolute_yggdrasil(pos,base,[0.08,-0.08])
        self.assertTrue(math.isfinite(a) and math.isfinite(b))
        self.assertGreater(work["public_edge_scans"],0)
        self.assertGreater(work["raw_bit_ops"],0)
        self.assertGreater(work["prospective_key_comparisons"],0)
        self.assertLessEqual(work["path_states"],256)
        self.assertNotAlmostEqual(a,b,places=10)
        hard,counter=q.forward("Yggdrasil",pos,base,[0.,0.])
        self.assertTrue(math.isfinite(hard))
        self.assertLessEqual(counter["max_active"],7)
        self.assertLessEqual(counter["max_retained"],9)

    def test_fit_only_no_oracle_and_original_inference(self):
        source_code=inspect.getsource(t.absolute_yggdrasil)
        for forbidden in ("public_routes(", "symbolic_routes(",
                          "protected(", "oracle_label", "correct_path"):
            self.assertNotIn(forbidden,source_code)
        self.assertEqual(evidence.SCHEMA,
                         "forge.research.f124t.new-fresh-absolute-causal-mass-development.v1")
        with self.assertRaises(source.Quarantined):
            source.protected()


if __name__=="__main__":
    unittest.main()
