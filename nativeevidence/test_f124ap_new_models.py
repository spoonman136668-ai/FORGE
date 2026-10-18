"""F124-AP focused preregistered TRAIN-only qualifications."""
import unittest,math,inspect
from collections import Counter
import f124ap_frozen_train_source as source
import f124ap_dual_kernel_learner as kernel
import f124ap_one_packed_hop_evidence as hop
import f124am_terminal_competition as original

YBASE=[.6,.7,.9,.5,.85,.15,-.55]
YDELTA=[.05,-.03]
WBASE=[.6,.7,.9,.5,.85,.15,-.55]
WDELTA=[.05,-.03,.02,-.04]

class F124APQualification(unittest.TestCase):
    def test_frozen_lineage_new_train_and_no_dev_construction(self):
        d=source.frozen()
        self.assertEqual(d["lineage"]["parent_pr"],525)
        self.assertEqual(source.witness.blob(source.FREEZE),source.FREEZE_BLOB)
        self.assertTrue(all(v is False for v in
                            d["qualification"]["authority"].values()))
        self.assertTrue(set(source.OPERATORS["TRAIN"]).isdisjoint(
                        source.OPERATORS["DEV"]))
        for lane in source.COHORTS:
            self.assertTrue(set(source.COHORTS[lane]["TRAIN"]).isdisjoint(
                            source.COHORTS[lane]["DEV"]))
            with self.assertRaises(Exception):
                source.pairs(lane,"DEV")
            rows=source.pairs(lane,"TRAIN")
            self.assertEqual(len(rows),48)
            self.assertEqual(Counter(row[2] for row in rows),
                             Counter({f:12 for f in source.FAMILIES}))
            ref=source.parent.parent.am.old.prior.parent.original.parent.prior.parent.routes15
            for seed,vec,fam,operator,nonce,pos,neg in rows[:4]:
                self.assertEqual(pos["demos"],neg["demos"])
                self.assertEqual(sum(source.relation(item["input_bits"],operator)!=
                       item["output_bits"] for item in pos["demos"]),3)
                self.assertEqual(ref(source.plain(pos,operator,nonce),
                                relaxed=fam=="rotate4_tolerant"),1)
                self.assertEqual(ref(source.plain(neg,operator,nonce),
                                relaxed=fam=="rotate4_tolerant"),0)

    def test_kernel_learns_transient_coefficients_from_public_examples_only(self):
        src=inspect.getsource(kernel)
        for forbidden in ("import f124ap_frozen_train_source",
                          "source.plain(","routes15(","inverse_output("):
            self.assertNotIn(forbidden,src)
        seed=source.COHORTS["Yggdrasil"]["TRAIN"].start
        fam,op,nonce,pos,neg,_=source.build(
            "Yggdrasil",seed,source.VECTORS[0],"TRAIN")
        for arch in kernel.KERNELS:
            raw,demos,task=kernel.public.public_task(pos)
            for reg in kernel.LAMBDAS:
                fitted,stats=kernel.fit(demos,arch,reg)
                predicted,confidence,operations=kernel.predict(
                    fitted,demos[20]["output_bits"])
                self.assertEqual(len(predicted),16)
                self.assertTrue(all(x in (0,1) for x in predicted))
                self.assertTrue(math.isfinite(confidence))
                self.assertEqual(stats["task_coefficients"],320)
                self.assertEqual(stats["training_gram_elements"],400)
                self.assertGreater(stats["max_transient_solver_elements"],0)
                norm,diag=kernel.normalize(pos,arch,reg,12,0.)
                self.assertFalse(diag["source_oracle_used"])
                self.assertEqual(diag["extra_cognitive_cells"],0)
                self.assertEqual(diag["public_train"],20)
                self.assertEqual(diag["public_validate"],4)
                if norm is not None:
                    self.assertEqual(len(norm["roles"]),len(pos["roles"]))
                score,work,obs=kernel.ygg(
                    pos,YBASE,YDELTA,arch,reg,12,0.)
                self.assertTrue(math.isfinite(score))
                if work is not None:
                    self.assertLessEqual(work["max_active"],7)
                    self.assertLessEqual(work["max_retained"],9)

    def test_one_packed_exact_original_and_new_hop_variants(self):
        seed=source.COHORTS["Wingless"]["TRAIN"].start
        fam,op,nonce,pos,neg,_=source.build(
            "Wingless",seed,source.VECTORS[0],"TRAIN")
        for graph in (source.plain(pos,op,nonce),
                      source.plain(neg,op,nonce)):
            expected,previous=original.terminal_competitive(
                graph,WBASE,WDELTA,0.)
            actual,w=hop.score(graph,WBASE,WDELTA,"original_gamma0",0.)
            self.assertEqual(actual,expected)
            self.assertEqual(w["edge_inspections"],previous["edge_inspections"])
            for mode in hop.MODES[1:]:
                for a in hop.ALPHAS[1:]:
                    value,work=hop.score(graph,WBASE,WDELTA,mode,a)
                    self.assertTrue(math.isfinite(value))
                    self.assertEqual(work["max_states_per_node"],1)
                    self.assertEqual(work["max_packed_bits_per_state"],12)
                    self.assertLessEqual(work["max_active"],64)
                    self.assertEqual(work["extra_retained_states"],0)
                    self.assertFalse(work["source_oracle_in_model"])
                    self.assertGreater(work["extra_hop_evidence_ops"],0)
if __name__=="__main__":unittest.main()
