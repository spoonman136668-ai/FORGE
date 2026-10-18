"""F124-AO frozen source lineage, public-only learning and original state limit."""
import unittest,inspect,math
from collections import Counter
import f124ao_frozen_source as s
import f124ao_public_relation_learner as y
import f124ao_packed_ambiguity as w
import f124am_terminal_competition as original

BASE_Y=[.6,.7,.9,.5,.85,.15,-.55]
BASE_W=[.6,.7,.9,.5,.85,.15,-.55]
DELTA=[.05,-.03,.02,-.04]

class FrozenAO(unittest.TestCase):
    def test_preimplementation_and_new_prospective_sources(self):
        doc=s.frozen()
        self.assertEqual(doc["lineage"]["parent_pr"],522)
        self.assertEqual(s.witness.blob(s.FREEZE),s.FREEZE_BLOB)
        self.assertTrue(all(v is False for v in doc["authority"].values()))
        self.assertFalse(set(s.OPERATORS["TRAIN"])&set(s.OPERATORS["DEV"]))
        for lane in s.COHORTS:
            self.assertFalse(set(s.COHORTS[lane]["TRAIN"])&
                             set(s.COHORTS[lane]["DEV"]))
            for phase in ("TRAIN","DEV"):
                seed=s.COHORTS[lane][phase].start
                fam,op,nonce,p,n,_=s.build(lane,seed,s.VECTORS[0],phase)
                self.assertEqual(p["demos"],n["demos"])
                self.assertEqual(sum(s.relation(x["input_bits"],op)!=
                      x["output_bits"] for x in p["demos"]),3)
                ref=s.parent.am.old.prior.parent.original.parent.prior.parent.routes15
                self.assertEqual(ref(s.plain(p,op,nonce),
                         relaxed=fam=="rotate4_tolerant"),1)
                self.assertEqual(ref(s.plain(n,op,nonce),
                         relaxed=fam=="rotate4_tolerant"),0)

    def test_public_learned_families_never_import_oracle(self):
        src=inspect.getsource(y)
        for forbidden in ("import f124ao_frozen_source","source.plain(",
                          "routes15(", "relation(", "true_inverse"):
            self.assertNotIn(forbidden,src)
        seed=s.COHORTS["Yggdrasil"]["TRAIN"].start
        fam,op,nonce,p,n,_=s.build("Yggdrasil",seed,s.VECTORS[0],"TRAIN")
        for arm in y.ARCHITECTURES:
            raw,demos,task=y.public.public_task(p)
            fitted,meta=y.build(demos,arm)
            bits,confidence,ops=y.predict(fitted,demos[22]["output_bits"])
            self.assertEqual(len(bits),16)
            self.assertGreaterEqual(confidence,0)
            self.assertGreater(ops,0)
            for bad in y.BAD_BITS:
                for margin in y.MARGINS:
                    norm,diagnostic=y.normalize(p,arm,bad,margin)
                    self.assertFalse(diagnostic["oracle_used"])
                    self.assertFalse(diagnostic["operator_identity_supplied"])
                    self.assertEqual(diagnostic["extra_retained_cells"],0)
                    if norm is not None:
                        self.assertEqual(set(norm),{"start","target","roles","edges"})
                        self.assertEqual(len(norm["roles"]),len(p["roles"]))
            score,work,diag=y.ygg(p,BASE_Y,DELTA,arm,2,1)
            self.assertTrue(math.isfinite(score))
            if work is not None:
                self.assertLessEqual(work["max_active"],7)
                self.assertLessEqual(work["max_retained"],9)

    def test_single_packed_original_gamma0_and_new_ephemeral_scores(self):
        seed=s.COHORTS["Wingless"]["TRAIN"].start
        fam,op,nonce,p,n,_=s.build("Wingless",seed,s.VECTORS[0],"TRAIN")
        for raw in (s.plain(p,op,nonce),s.plain(n,op,nonce)):
            exact,ow=original.terminal_competitive(raw,BASE_W,DELTA,0.)
            for mode in w.MODES:
                for alpha in ((0.,) if mode=="gamma0" else w.ALPHAS[1:]):
                    actual,work=w.score(raw,BASE_W,DELTA,mode,alpha)
                    self.assertTrue(math.isfinite(actual))
                    self.assertEqual(work["max_states_per_node"],1)
                    self.assertEqual(work["max_packed_bits_per_state"],12)
                    self.assertLessEqual(work["max_active"],64)
                    self.assertEqual(work["extra_retained_states"],0)
                    self.assertFalse(work["source_evaluator_normalization_included"])
                    if mode=="gamma0":
                        self.assertEqual(actual,exact)
                        self.assertEqual(work["edge_inspections"],ow["edge_inspections"])

if __name__=="__main__":unittest.main()
