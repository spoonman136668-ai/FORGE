"""F124-S isolated fresh-cohort, frozen source, continuous learning signal tests."""
import inspect
import math
import unittest

import f124s_anchored_surrogate as m
import f124q_independent_binding as qmodel
import f124q_fresh_source as original_q
import f124p_frozen_variants as ablations
import f124s_development_evidence as evidence


class TestF124S(unittest.TestCase):
    def test_preimplementation_and_parent_immutability(self):
        p=m.frozen()
        self.assertEqual(p["state"],"PREIMPLEMENTATION_FROZEN")
        self.assertEqual(p["parent"]["qualified_qg_run"],39080811300)
        self.assertEqual(m.git_blob(original_q.__file__),m.QSOURCE_BLOB)
        self.assertEqual(m.git_blob(qmodel.__file__),m.QMODEL_BLOB)
        self.assertTrue(all(x is False for x in p["authority"].values()))

    def test_new_cohort_disjoint_from_old_and_reserved(self):
        for lane in ("Wingless","Yggdrasil"):
            a=m.COHORTS[lane]
            for phase in ("FIT","DEV"):
                selected=set(a[phase])
                self.assertEqual(len(selected),24)
                self.assertTrue(selected.isdisjoint(original_q.COHORTS[lane]["FIT"]))
                self.assertTrue(selected.isdisjoint(original_q.COHORTS[lane]["DEV"]))
                self.assertTrue(selected.isdisjoint(original_q.FORBIDDEN[lane]))
            self.assertTrue(set(a["FIT"]).isdisjoint(a["DEV"]))
            with self.assertRaises(original_q.Quarantined):
                m.build(lane,180100,m.VECTORS[0],"DEV")
            for phase in ("FIT","DEV"):
                counts={7:0,8:0,9:0}
                for pos,neg in m.pairs(lane,phase):
                    self.assertTrue(original_q.paired_admit(pos,neg))
                    self.assertEqual(set(pos),{"start","target","roles","edges"})
                    counts[len(pos["roles"])]+=1
                self.assertEqual(counts,{7:16,8:16,9:16})

    def test_surrogate_changes_continuously_without_expanding_inference(self):
        lane="Yggdrasil"
        pos,neg=m.build(lane,590000,m.VECTORS[0],"FIT")
        base=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
        zero=[0.,0.]
        result,work=m.smooth_yggdrasil(pos,base,zero)
        self.assertTrue(math.isfinite(result))
        self.assertGreater(work["raw_bit_ops"],0)
        self.assertLessEqual(work["path_states"],256)
        self.assertGreater(work["prospective_key_comparisons"],0)
        changed,_=m.smooth_yggdrasil(pos,base,[.08,-.08])
        self.assertTrue(math.isfinite(changed))
        _,hard=qmodel.forward(lane,pos,base,zero)
        self.assertLessEqual(hard["max_active"],7)
        self.assertLessEqual(hard["max_retained"],9)
        self.assertTrue(math.isfinite(m.fit_loss(lane,[(pos,neg)],base,zero)[0]))

    def test_no_dev_or_oracle_in_trainer(self):
        training=inspect.getsource(m.train)+inspect.getsource(m.smooth_yggdrasil)
        self.assertNotIn('"DEV"',training)
        self.assertNotIn("public_routes(",training)
        self.assertNotIn("protected(",training)
        with self.assertRaises(original_q.Quarantined):
            m.smooth_yggdrasil({"oracle":True},[1.]*7,[0.,0.])
        self.assertEqual(evidence.ARMS,("original_F124O","prior_ablation",
                                        "new_F124S","fixed_12of16"))


if __name__=="__main__":
    unittest.main()
