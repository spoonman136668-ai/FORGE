"""F124-AT immutable-source and one-state research qualification."""
import math,unittest
import f124at_train_source as source
import f124at_train_evidence as analysis
import f124at_packed_collision_controls as pack
import f124as_noisy_inverse as y
BASE=[.6,.7,.9,.5,.85,.15,-.55]
WDELTA=[.05,-.03,.02,-.04]
class F124AT(unittest.TestCase):
    def test_frozen_before_model_source_only_and_no_dev(self):
        d=source.frozen()
        self.assertEqual(d["lineage"]["parent_pr"],534)
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertTrue(all(v is False for v in d["authority"].values()))
        self.assertTrue(set(source.OPERATORS["TRAIN"]).isdisjoint(source.OPERATORS["DEV"]))
        for lane in source.COHORTS:
            with self.assertRaises(Exception):source.pairs(lane,"DEV")
            self.assertTrue(set(source.COHORTS[lane]["TRAIN"]).isdisjoint(
                            source.COHORTS[lane]["DEV"]))
            seed=source.COHORTS[lane]["TRAIN"].start
            fam,op,nonce,p,n,_=source.build(lane,seed,source.VECTORS[0],"TRAIN")
            self.assertEqual(p["demos"],n["demos"])
            self.assertEqual(len(p["demos"]),24)
            self.assertEqual(sum(source.relation(d["input_bits"],op)!=d["output_bits"]
                                 for d in p["demos"]),3)

    def test_true_public_rank_and_fitted_original_are_bounded(self):
        seed=source.COHORTS["Yggdrasil"]["TRAIN"].start
        fam,op,nonce,p,n,_=source.build("Yggdrasil",seed,source.VECTORS[0],"TRAIN")
        fit,diag,demos=y.public_fit(p,"robust_affine_syndrome")
        self.assertEqual(len(demos),24)
        self.assertLessEqual(analysis.rank17(demos),17)
        self.assertEqual(diag["matrix_trials"],256)
        if fit is not None:
            bits,ops=y.infer(fit,demos[20]["output_bits"])
            self.assertEqual(len(bits),16)
            self.assertGreater(ops,0)

    def test_single_packed_alternatives_and_overbudget_explicit(self):
        seed=source.COHORTS["Wingless"]["TRAIN"].start
        fam,op,nonce,p,n,_=source.build("Wingless",seed,source.VECTORS[0],"TRAIN")
        for g in (source.plain(p,op,nonce),source.plain(n,op,nonce)):
            for key in pack.CHECKSUMS:
                s,w=pack.score12(g,BASE,WDELTA,key)
                self.assertTrue(math.isfinite(s))
                self.assertEqual(w["max_states_per_node"],1)
                self.assertEqual(w["max_packed_bits_per_state"],12)
                self.assertLessEqual(w["max_active"],64)
                collision=pack.collisions(g,pack.CHECKSUMS[key])
                self.assertGreaterEqual(collision["collision_pairs"],0)
            s,w=pack.full16_diagnostic(g,BASE,WDELTA)
            self.assertTrue(math.isfinite(s))
            self.assertTrue(w["overbudget_only"])
            self.assertEqual(w["max_packed_bits_per_state"],16)
if __name__=="__main__":unittest.main()
