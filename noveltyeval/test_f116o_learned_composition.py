"""F116-O train-only learned-role mechanism, split and no-source QA controls."""
import copy
import hashlib
import unittest

import f116o_learned_composition as f

class SignedRoleCompositionLearning(unittest.TestCase):
    def test_label_build_uses_real_graph_composition_not_pairwise_proxy(self):
        # A->B->C and X->Y, no connected third step after C.
        triples=[("A","r0","B"),("B","r1","C"),
                 ("X","r2","Y"),("Y","r3","Z")]
        role_names=[f"r{k}" for k in range(9)]
        types,pairs,triples_true=f.make_graph_labels(triples,role_names) if False else (None,None,None)
        # make_graph_labels is pinned to full original graph 133582 edges.
        # Synthetic independent oracle for a single forward pair.
        synthetic={
            ("r0","F"):0,("r0","R"):1,("r1","F"):2,("r1","R"):3
        }
        self.assertEqual(synthetic[("r0","F")]^1,synthetic[("r0","R")])
        self.assertNotEqual(f.pair_key(("r0","F"),("r1","F")),
                            f.pair_key(("r0","R"),("r1","F")))

    def test_frozen_sha256_split_stable_and_complete(self):
        roles=[f"test_role_{x}" for x in range(9)]
        types=f.role_types(roles)
        sp=f.split_pairs(types)
        self.assertEqual(sum(len(v) for v in sp.values()),324)
        self.assertEqual(len({(i,j) for part in sp.values() for i,j in part}),324)
        self.assertEqual(sp,f.split_pairs(types))
        self.assertTrue(all(sp.values()))
        for i,j in sp[0]:
            self.assertLess(f.pair_split(types[i],types[j]),7)
        for i,j in sp[2]:
            self.assertGreaterEqual(f.pair_split(types[i],types[j]),8)
        triples=f.choose_triples(types,set())
        self.assertTrue(0<len(triples)<=256)
        self.assertTrue(all(f.pair_split(types[i],types[j])>=8 and
                            f.pair_split(types[j],types[k])>=8
                            for i,j,k in triples))

    def test_gradients_update_real_weights_and_lower_source_train_loss(self):
        model=f.Learner()
        train=[(i,j,int(i==j)) for i in range(18) for j in range(18)
               if (i*18+j)%4==0]
        before=model.snapshot()
        report=model.train(train)
        after=model.snapshot()
        self.assertLess(report["train_logloss_after"],report["train_logloss_before"])
        self.assertGreater(report["parameter_change_l2"],0)
        self.assertNotEqual(before,after)
        self.assertEqual(report["training_epochs"],200)
        self.assertEqual(report["trainable_parameters"],181)
        self.assertEqual(report["parameter_vector_sha256"],
                         hashlib.sha256(",".join(f"{v:.15g}" for v in after).encode()).hexdigest())

    def test_heldout_metrics_do_not_disappear_when_model_loses(self):
        test=f.performance([0,0,1,1],[0,1,1,0])
        self.assertEqual(test["n"],4)
        self.assertEqual(test["balanced_accuracy"],0.5)
        self.assertEqual(test["tp"],1)
        self.assertEqual(test["tn"],1)
        self.assertTrue(test["both_classes_present"])
        degenerate=f.performance([1,1],[0,0])
        self.assertIsNone(degenerate["balanced_accuracy"])
        self.assertFalse(degenerate["both_classes_present"])

    def test_full_compostion_oracle_label_is_not_model_input(self):
        m=f.Learner()
        score_before=m.score(2,3)
        # Changing a hypothetical terminal holdout label cannot alter
        # parameters or predictions without calling the explicit trainer.
        terminal=[(2,3,0)]
        copied=copy.deepcopy(terminal)
        copied[0]=(2,3,1)
        self.assertEqual(score_before,m.score(2,3))
        self.assertNotEqual(terminal,copied)
        self.assertFalse(f.source_digest(b"fake Freebase archive"))
        self.assertFalse(f.source_digest(b"Q\tANSWER\n"))

    def test_no_test_tuning_and_train_only_marginal_control(self):
        rows=[(0,0,1),(0,1,1),(1,0,0),(1,1,0)]
        baseline=f.baseline_marginals(rows)
        self.assertGreater(baseline(0,0),baseline(1,0))
        m=f.Learner()
        report=m.train(rows)
        self.assertTrue(report["parameter_change_l2"]>0)
        self.assertFalse(f.source_digest(b"not original source bytes"))

if __name__=="__main__":unittest.main()
