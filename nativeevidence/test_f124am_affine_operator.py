"""F124-AM frozen source, robust in-context mapping and hard state limits."""
import unittest,inspect,math
from collections import Counter
import f124am_frozen_source as s
import f124am_example_affine_learner as m
import f124am_terminal_competition as newwing
import f124ak_one_packed_contrast as oldwing

class FrozenAM(unittest.TestCase):
    def test_frozen_protocol_and_disjoint_data(self):
        f=s.frozen()
        self.assertEqual(s.witness.blob(s.FREEZE),s.FREEZE_BLOB)
        self.assertEqual(f["lineage"]["qualified_run"],39115437034)
        self.assertTrue(all(v is False for v in f["authority"].values()))
        self.assertEqual(f["Yggdrasil"]["support_grid"],list(m.COUNTS))
        self.assertEqual(f["Wingless"]["gamma_grid"],list(m.GAMMAS))
        for lane in s.COHORTS:
            self.assertTrue(set(s.COHORTS[lane]["TRAIN"]).isdisjoint(
                            s.COHORTS[lane]["DEV"]))
            cases=s.pairs(lane,"TRAIN")
            self.assertEqual(len(cases),48)
            self.assertEqual(Counter(x[2] for x in cases),
                             Counter({x:12 for x in s.FAMILIES}))
            for seed,vec,fam,op,nonce,p,n in cases:
                self.assertEqual(p["demos"],n["demos"])
                self.assertEqual(len(p["demos"]),24)
                self.assertEqual(sum(s.relation(d["input_bits"],op)!=d["output_bits"]
                                     for d in p["demos"]),2)
                oracle=s.old.prior.parent.original.parent.prior.parent.routes15
                self.assertEqual(oracle(s.plain(p,op,nonce),
                                        relaxed=fam=="rotate4_tolerant"),1)
                self.assertEqual(oracle(s.plain(n,op,nonce),
                                        relaxed=fam=="rotate4_tolerant"),0)

    def test_source_invertibility_and_examples_outside_old_class(self):
        key=s.to_bits(0xAC39)
        for operator in s.OPERATORS["TRAIN"]+s.OPERATORS["DEV"]:
            self.assertEqual(s.relation(s.relation(key,operator),operator,True),
                             key)
        for seed,vec,fam,op,nonce,p,n in s.pairs("Yggdrasil","TRAIN")[:8]:
            restored,meta=m.normalize(p,24)
            # Wrong inferred maps are a SCIENTIFIC outcome, not a
            # source/provenance failure. Keep them visible in the untouched
            # scorer and per-family false-positive/false-negative report.
            if restored is not None:
                self.assertEqual(set(restored),{"start","target","roles","edges"})
                self.assertEqual(len(restored["roles"]),len(p["roles"]))
            self.assertFalse(meta["learner"]["source_operator_known"])

    def test_exact_original_one_state_gamma0(self):
        weights=[.6,.7,.9,.5,.85,.15,-.55]
        delta=[.05,-.03,.02,-.04]
        for seed,vec,fam,op,nonce,p,n in s.pairs("Wingless","TRAIN")[:8]:
            raw=s.plain(p,op,nonce)
            a,aw=oldwing.wing_competitive(raw,weights,delta,.5)
            b,bw=newwing.terminal_competitive(raw,weights,delta,0.)
            self.assertEqual((a,aw),(b,bw))
            for g in m.GAMMAS:
                value,work=newwing.terminal_competitive(raw,weights,delta,g)
                self.assertTrue(math.isfinite(value))
                self.assertEqual(work["max_states_per_node"],1)
                self.assertEqual(work["max_packed_bits_per_state"],12)
                self.assertLessEqual(work["max_active"],64)

    def test_ygg_fit_only_and_7_plus_9(self):
        cases=s.pairs("Yggdrasil","TRAIN")
        base=[.4,.9,.65,.75,.8,.2,-.5];delta=[1.3,.2]
        selected,grid=m.fit_support(cases,base,delta)
        self.assertEqual(len(grid),3)
        self.assertEqual(selected["paired"],max(x["paired"] for x in grid))
        for seed,vec,fam,op,nonce,p,n in cases[:8]:
            for graph in (p,n):
                score,work,diag=m.ygg(graph,base,delta,selected["count"])
                if work is not None:
                    self.assertLessEqual(work["max_active"],7)
                    self.assertLessEqual(work["max_retained"],9)
        module=inspect.getsource(m)
        for token in ("import f124am_frozen_source",
                      "s.relation(","source.plain(","routes15(","oracle("):
            self.assertNotIn(token,module)

if __name__=="__main__":unittest.main()
