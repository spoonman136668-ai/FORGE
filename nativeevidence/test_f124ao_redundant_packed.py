"""F124-AO prospectively frozen, never-old-DEV scientific source tests."""
import math,unittest,inspect
from collections import Counter
import f124ao_frozen_source as source
import f124ao_redundant_affine_and_packed as new
import f124ak_one_packed_contrast as baseline

class AO(unittest.TestCase):
    def test_original_source_and_new_public_support(self):
        p=source.frozen()
        self.assertEqual(p["original"]["run"],39118489510)
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertTrue(all(v is False for v in p["authority"].values()))
        for lane in source.COHORTS:
            self.assertTrue(set(source.COHORTS[lane]["TRAIN"]).isdisjoint(
                            source.COHORTS[lane]["DEV"]))
            cases=source.pairs(lane,"TRAIN")
            self.assertEqual(len(cases),48)
            self.assertEqual(Counter(a[2] for a in cases),
                        Counter({f:12 for f in source.FAMILIES}))
            for seed,vec,fam,op,nonce,p,n in cases:
                self.assertEqual(p["demos"],n["demos"])
                self.assertEqual(len(p["demos"]),40)
                self.assertEqual(sum(
                    source.relation(d["input_bits"],op)!=d["output_bits"]
                    for d in p["demos"]),3)
                oracle=source.prior.am.old.prior.parent.original.parent.prior.parent.routes15
                self.assertEqual(oracle(source.plain(p,op,nonce),
                        relaxed=fam=="rotate4_tolerant"),1)
                self.assertEqual(oracle(source.plain(n,op,nonce),
                        relaxed=fam=="rotate4_tolerant"),0)

    def test_sequential_one_packed_and_no_second_retained_state(self):
        base=[.6,.7,.9,.5,.85,.15,-.55]
        delta=[.05,-.03,.02,-.04]
        seed,v,fam,op,nonce,p,n=source.pairs("Wingless","TRAIN")[0]
        for g in (source.plain(p,op,nonce),
                  source.plain(n,op,nonce)):
            old,w=baseline.wing_competitive(g,base,delta,.5)
            once,onework=new.sequential_wing(g,base,delta,new.CHECKSUMS[0])
            self.assertEqual((old,w),(once,onework))
            for checksum in new.CHECKSUMS:
                score,work=new.sequential_wing(g,base,delta,checksum)
                self.assertTrue(math.isfinite(score))
                self.assertEqual(work["max_states_per_node"],1)
                self.assertEqual(work["max_packed_bits_per_state"],12)
                self.assertLessEqual(work["max_active"],64)

    def test_public_only_affine_fit_and_refusal_outside_class(self):
        case=source.pairs("Yggdrasil","TRAIN")
        for seed,v,fam,op,nonce,p,n in case[:8]:
            graph,diag=new.normalize(p,64,1)
            self.assertFalse(diag["learner"]["operator_label_seen"])
            self.assertLessEqual(diag["learner"]["trials"],64)
            if graph is not None:
                self.assertEqual(set(graph),{"start","target","roles","edges"})
        code=inspect.getsource(new)
        for forbidden in ("import f124ao_frozen_source",
                          "source.plain(","routes15(","oracle(",
                          "relation("):
            self.assertNotIn(forbidden,code)

if __name__=="__main__":unittest.main()
