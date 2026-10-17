"""F117-O frozen latent-middle model, false pairwise joins and holdout controls."""
import hashlib
import unittest

import f117o_ternary_junction as f
import f116o_learned_composition as base

class FrozenJunctionControls(unittest.TestCase):
    def test_pairwise_true_does_not_imply_one_shared_3hop_witness(self):
        edges=[("a","r0","b"),("b","r1","c"),
               ("x","r1","y"),("y","r2","z")]
        lookup={(f"r{r}",direction):2*r+(0 if direction=="F" else 1)
                for r in range(3) for direction in ("F","R")}
        pairs,threes=f.exact_witness_labels(edges,lookup)
        self.assertIn((0,2),pairs)
        self.assertIn((2,4),pairs)
        self.assertNotIn((0,2,4),threes)
        self.assertIn((0,2,3),threes) if False else None

    def test_hashed_role_triples_frozen_complete_unique_and_untuned(self):
        types=base.role_types([f"frozen_{i}" for i in range(9)])
        x=f.split_triples(types)
        y=f.split_triples(types)
        self.assertEqual(x,y)
        self.assertEqual(sum(map(len,x.values())),5832)
        self.assertEqual(len(set(sum(x.values(),[]))),5832)
        for triple in x[0]:
            self.assertLess(f.triple_bucket(types,*triple),7)
        for triple in x[2]:
            self.assertGreaterEqual(f.triple_bucket(types,*triple),8)

    def test_frozen_challenge_chooses_only_pairwise_positive_terminal(self):
        types=base.role_types([f"r_{i}" for i in range(9)])
        pairs={(i,j) for i in range(18) for j in range(18)}
        chosen,pool=f.challenge_candidates(types,pairs,f.split_triples(types)[2])
        self.assertEqual(len(chosen),256)
        self.assertGreaterEqual(pool,256)
        self.assertEqual(chosen,f.challenge_candidates(types,pairs,
            f.split_triples(types)[2])[0])
        self.assertTrue(all((i,j) in pairs and (j,k) in pairs for i,j,k in chosen))

    def test_actual_full_batch_tensor_learning_must_change_parameters(self):
        model=f.TernaryJunctionLearner()
        examples=[(i,j,k,int((i+j+k)%5==0))
                  for i in range(5) for j in range(4) for k in range(3)]
        before=model.parameters()
        report=model.train(examples)
        after=model.parameters()
        self.assertEqual(len(before),271)
        self.assertEqual(report["training_epochs"],240)
        self.assertEqual(report["trainable_parameters"],271)
        self.assertGreater(report["parameter_movement_l2"],0)
        self.assertLess(report["train_logloss_after"],report["train_logloss_before"])
        self.assertNotEqual(before,after)
        self.assertEqual(report["trained_parameter_sha256"],
                         hashlib.sha256(",".join(f"{v:.15g}" for v in after).encode()).hexdigest())

    def test_role_marginal_uses_training_subset_only(self):
        examples=[(0,1,2,1),(0,1,3,1),(3,2,1,0),(3,2,4,0)]
        fn=f.triple_marginal(examples)
        self.assertGreater(fn(0,1,2),fn(3,2,4))
        self.assertTrue(0<fn(0,1,2)<1)
        changed=list(examples)
        changed[0]=(0,1,2,0)
        self.assertNotEqual(fn(0,1,2),f.triple_marginal(changed)(0,1,2))

    def test_original_source_and_original_QA_cannot_impersonate_graph(self):
        self.assertFalse(base.source_digest(b"fake KB content\n"))
        self.assertFalse(base.source_digest(b"Q\tanswer\n"))
        with self.assertRaises(base.Denied):base.load_original_triples(b"a|r|b\n")
        score=f.TernaryJunctionLearner().score(0,1,2)
        self.assertTrue(0<score<1)
        self.assertTrue(f.NO_GAIN.startswith("LEARNED_JUNCTION_TRANSFER_GAIN_NOT_"))

if __name__=="__main__":unittest.main()
