"""F124-AV source, public query and original one-state capacity focused."""
import unittest,math
import f124av_train_source as src
import f124av_informative_inverse as inverse
import f124av_onepacked_handoff as wing
import f124av_fit_screen as run
import f124am_terminal_competition as original
YBASE=[.6,.7,.9,.5,.85,.15,-.55]
YDELTA=[.05,-.03]
WDELTA=[.05,-.03,.02,-.04]
class AV(unittest.TestCase):
    def test_preimplementation_source_and_DEV_inaccessible(self):
        d=src.frozen()
        self.assertEqual(d["lineage"]["parent_pr"],538)
        self.assertEqual(src.witness.blob(src.FREEZE),src.FREEZE_BLOB)
        self.assertTrue(all(v is False for v in d["authority"].values()))
        self.assertFalse(set(src.OPERATORS["TRAIN"])&set(src.OPERATORS["DEV"]))
        for lane in src.COHORTS:
            with self.assertRaises(Exception):src.pairs(lane,"DEV")
            a=run.rows(lane,"FIT");b=run.rows(lane,"SCREEN")
            self.assertEqual(len(a),len(b))
            self.assertEqual(len(a),24)
            self.assertFalse(set((r[0],r[1]) for r in a)&
                             set((r[0],r[1]) for r in b))
    def test_matched_public_query_count_and_corruptions(self):
        seed=src.COHORTS["Yggdrasil"]["TRAIN"].start
        fam,op,nonce,p,n,_=src.build("Yggdrasil",seed,src.VECTORS[0],"TRAIN")
        for cond in ("balanced_basis48","random48"):
            demo=src.active_public_demos(seed,src.VECTORS[0],op,cond,p["demos"])
            self.assertEqual(len(demo),48)
            self.assertEqual(sum(src.relation(x["input_bits"],op)!=x["output_bits"]
                                 for x in demo),6)
            start,check=demo[:40],demo[40:]
            self.assertEqual(len(start),40)
            self.assertEqual(len(check),8)
            coeff,info=inverse.fit(demo,nonce)
            self.assertEqual(info["all_ransac_attempts"],256)
            self.assertEqual(info["public_source_calls_total"],48)
            result=inverse.check(demo,coeff)
            self.assertLessEqual(result,128)
            for budget in inverse.BUDGETS:
                for minimum in inverse.CHECK_LIMITS:
                    value,work,diag=inverse.score(p,YBASE,YDELTA,
                                              coeff,info,result,budget,minimum)
                    self.assertTrue(math.isfinite(value))
                    self.assertFalse(diag["source_operator_known"])
                    if work is not None:
                        self.assertLessEqual(work["max_active"],7)
                        self.assertLessEqual(work["max_retained"],9)
    def test_one_12bit_packed_state_and_no_extra_cache(self):
        seed=src.COHORTS["Wingless"]["TRAIN"].start
        fam,op,nonce,p,n,_=src.build("Wingless",seed,src.VECTORS[0],"TRAIN")
        for g in (src.plain(p,op,nonce),src.plain(n,op,nonce)):
            baseline,orig_work=original.terminal_competitive(g,YBASE,WDELTA,0.)
            self.assertTrue(math.isfinite(baseline))
            for mode in ("weak_handoff_gap","rival_overconfidence"):
                for alpha in (.04,.10,.20):
                    score,work=wing.score(g,YBASE,WDELTA,mode,alpha)
                    self.assertTrue(math.isfinite(score))
                    self.assertEqual(work["max_states_per_node"],1)
                    self.assertEqual(work["max_packed_bits_per_state"],12)
                    self.assertEqual(work["max_encoded_cache"],0)
                    self.assertEqual(work["max_lookahead_cache"],0)
                    self.assertLessEqual(work["max_active"],64)
if __name__=="__main__":unittest.main()
