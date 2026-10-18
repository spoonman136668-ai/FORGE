"""F124-AR exact frozen source and noninterfering diagnostic mechanism tests."""
import math,unittest
import f124ar_frozen_train_source as source
import f124ar_train_diagnostic as diag
import f124aq_sparse_composition as y
import f124aq_local_contrast as w
import f124am_terminal_competition as original

YBASE=[.6,.7,.9,.5,.85,.15,-.55]
YDELTA=[.05,-.03]
WDELTA=[.05,-.03,.02,-.04]

class SourceFrozen(unittest.TestCase):
    def test_exact_identity_and_train_only(self):
        freeze=source.frozen()
        self.assertEqual(freeze["source_parent"]["pr"],531)
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertTrue(all(x is False for x in freeze["qualification"]["authority"].values()))
        self.assertFalse(set(source.OPERATORS["TRAIN"])&set(source.OPERATORS["DEV"]))
        for lane in source.COHORTS:
            self.assertFalse(set(source.COHORTS[lane]["TRAIN"])&
                             set(source.COHORTS[lane]["DEV"]))
            with self.assertRaises(Exception):source.pairs(lane,"DEV")
            for seed in (source.COHORTS[lane]["TRAIN"].start,
                         source.COHORTS[lane]["TRAIN"].stop-1):
                fam,op,nonce,p,n,_=source.build(lane,seed,source.VECTORS[0],"TRAIN")
                self.assertEqual(p["demos"],n["demos"])
                self.assertEqual(sum(source.relation(d["input_bits"],op)!=
                    d["output_bits"] for d in p["demos"]),3)
                demo=p["demos"][0]
                original_bits=source.relation(
                    source.relation(demo["input_bits"],op),op,True)
                self.assertEqual(original_bits,demo["input_bits"])

    def test_diag_is_not_candidate_training_with_truth(self):
        seed=source.COHORTS["Yggdrasil"]["TRAIN"].start
        fam,op,nonce,p,n,_=source.build(
            "Yggdrasil",seed,source.VECTORS[0],"TRAIN")
        raw,demos,_=y.public.public_task(p)
        fitted,fit=y.train(demos,"sparse_xor_basis",2)
        pred,cost=y.predict(fitted,demos[0]["output_bits"])
        self.assertEqual(len(pred),16)
        self.assertGreater(fit["fit_feature_bitset_storage_bits"],0)
        self.assertGreater(cost,0)
        self.assertIsInstance(diag.transition(raw,YBASE,YDELTA),float)
        truth=diag.source_oracle(p,op,nonce)
        self.assertEqual(len(truth["roles"]),len(p["roles"]))

    def test_wing_baseline_unmodified_and_one_packed(self):
        seed=source.COHORTS["Wingless"]["TRAIN"].start
        fam,op,nonce,p,n,_=source.build(
            "Wingless",seed,source.VECTORS[0],"TRAIN")
        for graph in (source.plain(p,op,nonce),source.plain(n,op,nonce)):
            control,prior=original.terminal_competitive(
                graph,YBASE,WDELTA,0.)
            self.assertTrue(math.isfinite(control))
            new,work=w.score(graph,YBASE,WDELTA,
                             "relative_lookahead_contrast",.12)
            self.assertTrue(math.isfinite(new))
            self.assertEqual(work["max_states_per_node"],1)
            self.assertEqual(work["max_packed_bits_per_state"],12)
            self.assertEqual(work["extra_retained_states"],0)
            self.assertLessEqual(work["max_active"],64)
            self.assertFalse(work["source_oracle_in_model"])
if __name__=="__main__":unittest.main()
