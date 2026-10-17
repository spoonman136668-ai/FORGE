"""F119-O directed source state, negative path-bag, real learned gates."""
import hashlib
import unittest
import f119o_root_conditioned_propagation as f
import f116o_learned_composition as kb

class FrozenRootStatePropagation(unittest.TestCase):
    def test_two_real_connected_paths_have_shared_middle_state(self):
        triples=[
            ("a","r1","b"),("b","r2","c"),
            ("a","r3","d"),("d","r4","e"),
            ("x","r2","y"),("a","r0","x"),
        ]
        roles=[f"r{i}" for i in range(9)]
        out,types=f.adjacency(triples,roles)
        hist=f.full_two_step_histogram("a",out)
        self.assertIsNotNone(hist)
        exact=(types[("r1","F")],types[("r2","F")])
        self.assertGreater(hist["c"][exact],0)
        self.assertEqual(hist["e"].get(exact,0),0)
        self.assertGreater(sum(hist["e"].values()),0)
        task=f.freeze_query("a",hist)
        self.assertIsNotNone(task)
        self.assertNotEqual(task[2],task[3])
        query=task[1]
        self.assertEqual(int(task[2].get(query,0)>0)+int(task[3].get(query,0)>0),1)

    def test_separately_existent_unjoined_roles_cannot_make_fake_path(self):
        triples=[("a","r1","b"),("x","r2","z"),("x","r3","t")]
        roles=[f"r{i}" for i in range(9)]
        out,types=f.adjacency(triples,roles)
        hist=f.full_two_step_histogram("a",out)
        q=(types[("r1","F")],types[("r2","F")])
        self.assertEqual(sum(c.get(q,0) for c in hist.values()),0)
        # The original physical fact a-r1-b cannot be reused backward to a.
        self.assertNotIn("a",hist)

    def test_budget_denial_does_not_truncate_to_fake_success(self):
        roles=[f"r{i}" for i in range(9)]
        triples=[("root","r1",f"n{i:03d}") for i in range(130)]
        out,_=f.adjacency(triples,roles)
        self.assertIsNone(f.full_two_step_histogram("root",out))

    def test_real_numerical_role_weights_and_train_only_gradients(self):
        model=f.LearnedTypedState()
        train=[]
        for i in range(12):
            hist_pos={(0,1):3,(4,5):1}
            hist_neg={(2,3):1}
            correct_first=(i%2==0)
            train.append((f"synthetic-{i}",(0,1),
                         hist_pos if correct_first else hist_neg,
                         hist_neg if correct_first else hist_pos,
                         int(correct_first)))
        original=model.params()
        result=model.train(train)
        self.assertEqual(result["trainable_parameters"],109)
        self.assertEqual(result["training_epochs"],120)
        self.assertGreater(result["parameter_l2_movement"],0)
        self.assertLess(result["train_logloss_final"],result["train_logloss_initial"])
        self.assertNotEqual(original,model.params())
        self.assertEqual(result["learned_parameter_sha256"],
            hashlib.sha256(",".join(f"{x:.8f}" for x in model.params()).encode()).hexdigest())

    def test_root_split_and_candidate_order_are_predeclared(self):
        for name in ("a","b","source_23","Entity_with_spaces"):
            self.assertEqual(f.split(name),f.split(name))
            self.assertEqual(f.order_hash(name),f.order_hash(name))
        self.assertNotEqual(f.h("node_a"),f.h("node_b"))
        self.assertFalse(kb.source_digest(b"fake source data\n"))
        with self.assertRaises(f.Denied):
            f.audit(b"fake source data\n")

    def test_no_explicit_node_equality_feature_or_qa_leak(self):
        model=f.LearnedTypedState()
        self.assertEqual(len(model.params()),109)
        gates=model.gate()
        self.assertEqual(len(gates),18)
        self.assertEqual(len(gates[0]),18)
        self.assertTrue(all(0.0<p<1.0 for row in gates for p in row))
        self.assertEqual(f.N,18)
        self.assertEqual(f.D,3)

if __name__=="__main__":unittest.main()
