"""F124-U frozen independent public-source and bounded interventions tests."""
import inspect
import math
import unittest

import f124u_interventions as u
import f124u_development_evidence as evidence
import f124t_absolute_binding as prior
import f124q_independent_binding as inference
import f124q_fresh_source as public


class FrozenF124U(unittest.TestCase):
    def test_original_sources_and_preimplementation_freeze(self):
        spec=u.frozen()
        self.assertEqual(u.git_blob(u.FREEZE),u.FREEZE_BLOB)
        self.assertEqual(u.git_blob(prior.__file__),u.T_SOURCE_BLOB)
        self.assertEqual(spec["lineage"]["qualified_f124t_run"],39082424955)
        self.assertTrue(spec["reporting"]["no_extra_training"])
        self.assertTrue(all(x is False for x in spec["authority"].values()))

    def test_all_fresh_adversarial_public_cohorts(self):
        for lane in ("Wingless","Yggdrasil"):
            for phase in ("FIT","DEV"):
                seeds=set(u.COHORTS[lane][phase])
                self.assertEqual(len(seeds),24)
                self.assertTrue(seeds.isdisjoint(prior.COHORTS[lane]["FIT"]))
                self.assertTrue(seeds.isdisjoint(prior.COHORTS[lane]["DEV"]))
                self.assertTrue(seeds.isdisjoint(public.COHORTS[lane]["FIT"]))
                self.assertTrue(seeds.isdisjoint(public.COHORTS[lane]["DEV"]))
                count={7:0,8:0,9:0}
                cases=u.pairs(lane,phase)
                self.assertEqual(len(cases),48)
                for seed,vector,pos,neg in cases:
                    self.assertTrue(public.paired_admit(pos,neg))
                    self.assertEqual(set(pos),{"start","target","roles","edges"})
                    count[len(pos["roles"])]+=1
                self.assertEqual(count,{7:16,8:16,9:16})
            self.assertTrue(set(u.COHORTS[lane]["FIT"]).isdisjoint(u.COHORTS[lane]["DEV"]))
            with self.assertRaises(public.Quarantined):
                u.build(lane,680000,[2,1,1],"DEV")

    def test_calibration_frozen_grid_no_dev(self):
        sample=u.pairs("Wingless","FIT")
        original=[0.5,0.4,0.9,0.3,0.7,0.2,-0.1]
        win,grid=u.choose_fit_bias(sample,original,[0.,0.,0.,0.])
        self.assertEqual(len(grid),7)
        self.assertIn(win["bias"],u.GRID)
        self.assertEqual(grid[3]["bias"],0.)
        self.assertEqual(max(x["paired"] for x in grid),win["paired"])
        self.assertNotIn('"DEV"',inspect.getsource(u.choose_fit_bias))

    def test_new_cell_values_stay_bounded_and_label_blind(self):
        lane="Yggdrasil"
        _,_,pos,neg=u.pairs(lane,"FIT")[0]
        base=[0.4,0.9,0.65,0.75,0.8,0.2,-0.5]
        delta=[.3,-.1]
        for g in (pos,neg):
            original_logit,work=inference.forward(lane,g,base,delta)
            score,new_work=u.yggdrasil_value_intervention(g,base,delta)
            self.assertTrue(math.isfinite(original_logit))
            self.assertTrue(math.isfinite(score))
            self.assertEqual(new_work["max_active"]<=7,True)
            self.assertEqual(new_work["max_retained"]<=9,True)
            self.assertGreater(new_work["public_edge_scans"],0)
        script=inspect.getsource(u.yggdrasil_value_intervention)
        for forbidden in ("public_routes(","symbolic_routes(","protected(","true_label","oracle_path"):
            self.assertNotIn(forbidden,script)
        with self.assertRaises(public.Quarantined):
            u.yggdrasil_value_intervention({"oracle":True},base,delta)

    def test_strict_arm_enumeration(self):
        self.assertEqual(len(evidence.ARMS["Wingless"]),5)
        self.assertEqual(len(evidence.ARMS["Yggdrasil"]),6)
        self.assertEqual(evidence.T_SHA,
                         "a2f7b3641c2f84f684372918849170c97912c7a104fa4dbe264bcbd6d444c2d2")


if __name__=="__main__":
    unittest.main()
