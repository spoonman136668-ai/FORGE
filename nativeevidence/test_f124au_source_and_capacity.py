"""F124-AU focused preflight: source provenance, public learning, capacity."""
import unittest, math
import f124au_train_source as source
import f124au_parity_inverse as inv
import f124au_onepacked_policy as pack
import f124au_fit_screen_evidence as eval
import f124at_packed_collision_controls as orig

BASE=[.6,.7,.9,.5,.85,.15,-.55]
YDELTA=[.05,-.03]
WDELTA=[.05,-.03,.02,-.04]
class AU(unittest.TestCase):
    def test_frozen_first_and_unconstructed_dev(self):
        contract=source.frozen()
        self.assertEqual(contract["lineage"]["parent_pr"],535)
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertTrue(all(v is False for v in contract["authority"].values()))
        self.assertTrue(set(source.OPERATORS["TRAIN"]).isdisjoint(
                        source.OPERATORS["DEV"]))
        for lane in source.COHORTS:
            with self.assertRaises(Exception):source.pairs(lane,"DEV")
            self.assertTrue(set(source.COHORTS[lane]["TRAIN"]).isdisjoint(
                            source.COHORTS[lane]["DEV"]))
            seed=source.COHORTS[lane]["TRAIN"].start
            fam,op,nonce,p,n,_=source.build(lane,seed,source.VECTORS[0],"TRAIN")
            self.assertEqual(len(p["demos"]),24)
            self.assertEqual(p["demos"],n["demos"])
            self.assertEqual(sum(source.relation(d["input_bits"],op)!=
                d["output_bits"] for d in p["demos"]),3)
            rows=source.pairs(lane,"TRAIN")
            fit=eval.subset(rows,lane,"FIT")
            screen=eval.subset(rows,lane,"SCREEN")
            self.assertEqual(len(fit),24)
            self.assertEqual(len(screen),24)
            self.assertFalse(set(x[0:2] for x in fit)&
                             set(x[0:2] for x in screen))

    def test_parity_uses_public_only_and_checks(self):
        seed=source.COHORTS["Yggdrasil"]["TRAIN"].start
        fam,op,nonce,p,n,_=source.build("Yggdrasil",seed,
                                        source.VECTORS[0],"TRAIN")
        graph,demos,task=inv.public.public_task(p)
        for degree in inv.DEGREES:
            coeff,diag=inv.learn(demos,degree)
            self.assertEqual(len(coeff),16)
            self.assertEqual(diag["fit_rows"],20)
            self.assertTrue(diag["extra_model_memory_outside_7_plus_9"])
            output=inv.predict(coeff,demos[0]["output_bits"])
            self.assertEqual(len(output),16)
            for threshold in inv.CHECK_LIMITS:
                val,work,meta=inv.score(p,BASE,YDELTA,coeff,threshold)
                self.assertTrue(math.isfinite(val))
                self.assertFalse(meta["operator_known"])
                if work:
                    self.assertLessEqual(work["max_active"],7)
                    self.assertLessEqual(work["max_retained"],9)

    def test_one_original_packed_state_never_multiple(self):
        seed=source.COHORTS["Wingless"]["TRAIN"].start
        fam,op,nonce,p,n,_=source.build("Wingless",seed,
                                        source.VECTORS[0],"TRAIN")
        for graph in (source.plain(p,op,nonce),source.plain(n,op,nonce)):
            baseline,prior=orig.score12(graph,BASE,WDELTA,
                  "original_gamma0_checksum_1342")
            self.assertTrue(math.isfinite(baseline))
            self.assertEqual(prior["max_states_per_node"],1)
            for policy in pack.GRID:
                score,work=pack.score(graph,BASE,WDELTA,policy)
                self.assertTrue(math.isfinite(score))
                self.assertEqual(work["max_states_per_node"],1)
                self.assertEqual(work["max_packed_bits_per_state"],12)
                self.assertEqual(work["independently_scored_alternatives"],0)
                self.assertLessEqual(work["max_active"],64)

if __name__=="__main__":unittest.main()
