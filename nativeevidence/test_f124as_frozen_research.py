"""F124-AS independent preregistration and prospective model boundary tests."""
from __future__ import annotations
import unittest,math
import f124as_train_source as src
import f124as_noisy_inverse as ygg
import f124as_packed_fork_causality as wing
import f124am_terminal_competition as original

YBASE=[.6,.7,.9,.5,.85,.15,-.55]
YDELTA=[.05,-.03]
WDELTA=[.05,-.03,.02,-.04]
class ASFocused(unittest.TestCase):
    def test_frozen_parent_and_dev_rejected(self):
        frozen=src.frozen()
        self.assertEqual(src.witness.blob(src.FREEZE),src.FREEZE_BLOB)
        self.assertEqual(frozen["parent"]["pr"],532)
        self.assertFalse(set(src.OPERATORS["TRAIN"]) & set(src.OPERATORS["DEV"]))
        self.assertTrue(all(v is False for v in frozen["authority"].values()))
        for lane in src.COHORTS:
            with self.assertRaises(Exception):src.pairs(lane,"DEV")
            a=src.COHORTS[lane]["TRAIN"].start
            fam,op,nonce,p,n,_=src.build(lane,a,src.VECTORS[0],"TRAIN")
            self.assertEqual(len(p["demos"]),24)
            self.assertEqual(p["demos"],n["demos"])
            self.assertEqual(sum(src.relation(d["input_bits"],op)!=d["output_bits"]
                                 for d in p["demos"]),3)

    def test_inverse_public_fit_only_and_memory(self):
        seed=src.COHORTS["Yggdrasil"]["TRAIN"].start
        fam,op,nonce,p,n,_=src.build("Yggdrasil",seed,src.VECTORS[0],"TRAIN")
        for mode in ygg.MODES:
            fitted,info,demos=ygg.public_fit(p,mode)
            self.assertEqual(len(demos),24)
            self.assertEqual(info["matrix_trials"],256)
            self.assertTrue(info["additional_model_memory_reported"])
            if fitted is not None:
                pred,operations=ygg.infer(fitted,demos[20]["output_bits"])
                self.assertEqual(len(pred),16)
                self.assertGreater(operations,0)
            for budget in ygg.ERROR_BUDGET:
                for valid in ygg.MIN_CHECK:
                    score,work,meta=ygg.ygg(p,YBASE,YDELTA,fitted,info,budget,valid)
                    self.assertTrue(math.isfinite(score))
                    self.assertFalse(meta.get("source_oracle_used",False))
                    if work:
                        self.assertLessEqual(work["max_active"],7)
                        self.assertLessEqual(work["max_retained"],9)

    def test_original_gamma0_identity_and_one_state(self):
        seed=src.COHORTS["Wingless"]["TRAIN"].start
        fam,op,nonce,p,n,_=src.build("Wingless",seed,src.VECTORS[0],"TRAIN")
        for g in (src.plain(p,op,nonce),src.plain(n,op,nonce)):
            original_score,ow=original.terminal_competitive(g,YBASE,WDELTA,0.)
            same,w=wing.score(g,YBASE,WDELTA,"original_gamma0",0.)
            self.assertEqual(same,original_score)
            self.assertEqual(w["edge_inspections"],ow["edge_inspections"])
            for mode in wing.MODES[1:]:
                for alpha in wing.ALPHAS[1:]:
                    value,work=wing.score(g,YBASE,WDELTA,mode,alpha)
                    self.assertTrue(math.isfinite(value))
                    self.assertEqual(work["max_states_per_node"],1)
                    self.assertEqual(work["max_packed_bits_per_state"],12)
                    self.assertEqual(work["extra_retained_states"],0)
                    self.assertLessEqual(work["max_active"],64)

if __name__=="__main__":unittest.main()
