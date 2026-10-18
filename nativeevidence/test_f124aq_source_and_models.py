"""F124-AQ immutable source, public learned feature composition, one-state safety."""
import unittest,math,inspect
from collections import Counter
import f124aq_train_source as source
import f124aq_sparse_composition as y
import f124aq_local_contrast as w
import f124am_terminal_competition as original
BASE=[.6,.7,.9,.5,.85,.15,-.55]
YDELTA=[.05,-.03]
WDELTA=[.05,-.03,.02,-.04]

class F124AQFrozen(unittest.TestCase):
    def test_frozen_new_train_and_inaccessible_dev(self):
        d=source.frozen()
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertEqual(d["lineage"]["parent_pr"],528)
        self.assertTrue(all(v is False for v in d["qualification"]["authority"].values()))
        self.assertFalse(set(source.OPERATORS["TRAIN"])&set(source.OPERATORS["DEV"]))
        for lane in source.COHORTS:
            self.assertFalse(set(source.COHORTS[lane]["TRAIN"])&
                             set(source.COHORTS[lane]["DEV"]))
            with self.assertRaises(Exception):
                source.pairs(lane,"DEV")
            rows=source.pairs(lane,"TRAIN")
            self.assertEqual(len(rows),48)
            self.assertEqual(Counter(x[2] for x in rows),
                             Counter({f:12 for f in source.FAMILIES}))
            for seed,vec,fam,op,nonce,p,n in rows[:4]:
                self.assertEqual(p["demos"],n["demos"])
                self.assertEqual(sum(source.relation(d["input_bits"],op)!=d["output_bits"]
                                     for d in p["demos"]),3)
                for d in p["demos"][:4]:
                    value=source.relation(source.relation(d["input_bits"],op),op,True)
                    self.assertEqual(value,d["input_bits"])

    def test_public_greedy_composition_and_extra_memory_census(self):
        src=inspect.getsource(y)
        for forbidden in ("import f124aq_train_source","source.plain(",
                          "routes15(","relation(","inverse_output("):
            self.assertNotIn(forbidden,src)
        seed=source.COHORTS["Yggdrasil"]["TRAIN"].start
        fam,op,nonce,p,n,_=source.build(
            "Yggdrasil",seed,source.VECTORS[0],"TRAIN")
        graph,demos,opaque=y.public.public_task(p)
        self.assertEqual(len(demos),24)
        for mode in y.MODES:
            for terms in y.MAX_TERMS:
                fit,census=y.train(demos,mode,terms)
                output,cost=y.predict(fit,demos[20]["output_bits"])
                self.assertEqual(len(output),16)
                self.assertTrue(all(x in (0,1) for x in output))
                self.assertGreater(census["fit_feature_bitset_storage_bits"],0)
                self.assertTrue(census["additional_model_memory_reported"])
                self.assertGreater(cost,0)
                for wrong in y.VALID_WRONG:
                    result,meta=y.normalize(p,mode,terms,wrong)
                    self.assertFalse(meta["source_oracle_used"])
                    self.assertTrue(meta["transient_model_storage_disclosed"])
                    self.assertEqual(meta["extra_cognitive_cells"],0)
                    if result is not None:
                        self.assertEqual(set(result),{"start","target","roles","edges"})
                score,work,_=y.ygg(p,BASE,YDELTA,mode,terms,32)
                self.assertTrue(math.isfinite(score))
                if work is not None:
                    self.assertLessEqual(work["max_active"],7)
                    self.assertLessEqual(work["max_retained"],9)

    def test_original_gamma0_identity_and_new_single_packed_contrast(self):
        seed=source.COHORTS["Wingless"]["TRAIN"].start
        fam,op,nonce,p,n,_=source.build(
            "Wingless",seed,source.VECTORS[0],"TRAIN")
        for g in (source.plain(p,op,nonce),source.plain(n,op,nonce)):
            exact,legacy=original.terminal_competitive(g,BASE,WDELTA,0.)
            actual,work=w.score(g,BASE,WDELTA,"original_gamma0",0.)
            self.assertEqual(actual,exact)
            self.assertEqual(work["edge_inspections"],legacy["edge_inspections"])
            for mode in w.MODES[1:]:
                for alpha in w.ALPHAS[1:]:
                    val,counters=w.score(g,BASE,WDELTA,mode,alpha)
                    self.assertTrue(math.isfinite(val))
                    self.assertEqual(counters["max_states_per_node"],1)
                    self.assertEqual(counters["max_packed_bits_per_state"],12)
                    self.assertLessEqual(counters["max_active"],64)
                    self.assertEqual(counters["extra_retained_states"],0)
                    self.assertFalse(counters["source_oracle_in_model"])
if __name__=="__main__":unittest.main()
