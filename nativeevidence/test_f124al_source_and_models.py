"""F124-AL frozen source, genuinely nonlinear rules and one-packed parity."""
import inspect,math,unittest
from collections import Counter
import f124al_frozen_source as s
import f124al_noisy_operator_learner as m
import f124al_packed_confidence as capped
import f124ak_one_packed_contrast as original
import f124ae_scoring_transfer as old

class F124AL(unittest.TestCase):
    def test_frozen_source_and_disjoint_symmetric_noise(self):
        plan=s.frozen()
        self.assertEqual(s.git.blob(s.FREEZE),s.FREEZE_BLOB)
        self.assertEqual(plan["lineage"]["parent_action"],39114109672)
        self.assertEqual(plan["Yggdrasil"]["grid_support"],list(m.SUPPORT))
        self.assertEqual(plan["Wingless"]["grid_cap"],list(m.CAPS))
        self.assertTrue(all(v is False for v in plan["authority"].values()))
        for lane in s.COHORTS:
            self.assertTrue(set(s.COHORTS[lane]["TRAIN"]).isdisjoint(
                            s.COHORTS[lane]["DEV"]))
            for phase in ("TRAIN","DEV"):
                cases=s.pairs(lane,phase)
                self.assertEqual(len(cases),48)
                self.assertEqual(Counter(x[2] for x in cases),
                                 Counter({f:12 for f in s.FAMILIES}))
                for seed,v,fam,op,tag,p,n in cases:
                    self.assertEqual(p["demos"],n["demos"])
                    self.assertEqual(len(p["demos"]),24)
                    self.assertEqual(s.prior.parent.original.parent.prior.parent.routes15(
                        s.plain(p,op,tag),relaxed=fam=="rotate4_tolerant"),1)
                    self.assertEqual(s.prior.parent.original.parent.prior.parent.routes15(
                        s.plain(n,op,tag),relaxed=fam=="rotate4_tolerant"),0)
                    if v==tuple(s.VECTORS[0]):
                        self.assertEqual(p["demos"][0],p["demos"][1])

    def test_true_new_relations_invertible_and_noise_robust(self):
        x=s.bits(0xA671)
        for op in s.OPERATORS["TRAIN"]+s.OPERATORS["DEV"]:
            self.assertEqual(s.relation(s.relation(x,op),op,True),x)
        for seed,v,fam,op,tag,p,n in s.pairs("Yggdrasil","TRAIN")[:12]:
            recovered,diagnostic=m.normalize(p,24)
            self.assertTrue(diagnostic["learn"]["candidate_count"]>0)
            if recovered is not None:
                self.assertEqual(recovered,s.plain(p,op,tag))
        module=inspect.getsource(m)
        for forbidden in ("import f124al_frozen_source",
                          "source.relation(","truth_mapping(",
                          "plain(","routes15(","oracle(", '"DEV"'):
            self.assertNotIn(forbidden,module)

    def test_original_one_packed_cap1_and_memory(self):
        base=[.6,.7,.9,.5,.85,.15,-.55];delta=[.05,-.03,.02,-.04]
        cases=s.pairs("Wingless","TRAIN")
        for seed,v,fam,op,tag,p,n in cases[:10]:
            for g in (p,n):
                source_g=s.plain(g,op,tag)
                original_score,original_work=original.wing_competitive(
                    source_g,base,delta,.5)
                cap_score,cap_work=capped.competitive_capped(
                    source_g,base,delta,1.)
                self.assertEqual(cap_score,original_score)
                self.assertEqual(cap_work,original_work)
                self.assertEqual(cap_work["max_states_per_node"],1)
                self.assertEqual(cap_work["max_packed_bits_per_state"],12)
                for cap in m.CAPS:
                    score,w=capped.competitive_capped(source_g,base,delta,cap)
                    self.assertTrue(math.isfinite(score))
                    self.assertLessEqual(w["max_active"],64)

    def test_train_only_selection(self):
        ybase=[.4,.9,.65,.75,.8,.2,-.5];ydelta=[1.3,.2]
        win,grid=m.select_support(s.pairs("Yggdrasil","TRAIN"),ybase,ydelta)
        self.assertEqual(len(grid),4)
        self.assertEqual(win["paired"],max(x["paired"] for x in grid))
        wbase=[.6,.7,.9,.5,.85,.15,-.55];wdelta=[.05,-.03,.02,-.04]
        selected,allcaps=m.select_wing_cap(
            s.pairs("Wingless","TRAIN"),wbase,wdelta,win["count"])
        self.assertEqual(len(allcaps),6)
        self.assertIn(selected["cap"],m.CAPS)

if __name__=="__main__":unittest.main()
