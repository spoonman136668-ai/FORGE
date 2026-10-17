"""F118-O negative controls for exact graph joins and node-disjoint training."""
import hashlib
import unittest

import f118o_heldout_node_binding as f
import f116o_learned_composition as base

class UnseenNodeBindingFixtures(unittest.TestCase):
    def test_real_source_edge_join_and_broken_negative(self):
        triples=[("A","role.one","B"),("B","role.two","C"),
                 ("A2","role.one","D"),("D","role.two","E"),
                 ("B","role.two","C")]
        incoming,outgoing,source_set,eligible=f.source_edges(triples)
        self.assertIn("B",eligible)
        self.assertIn("D",eligible)
        self.assertEqual(incoming["B"],("A","role.one","B"))
        self.assertEqual(outgoing["B"],("B","role.two","C"))
        self.assertEqual(outgoing["D"],("D","role.two","E"))
        self.assertNotEqual(incoming["B"][2],outgoing["D"][0])
        self.assertIn(outgoing["D"],source_set)

    def test_frozen_sha_splits_unseen_and_negative_same_nibble(self):
        # Synthetic names only; authentic source denominator is enforced in audit.
        nodes=sorted([f"fake_node_{i:05d}" for i in range(8192)],
                     key=f.sort_key)
        selected,negative,source_counts=f.frozen_candidates(nodes)
        self.assertEqual(len(selected["train"]),512)
        self.assertEqual(len(selected["dev"]),128)
        self.assertEqual(len(selected["test"]),256)
        self.assertEqual(sum(source_counts.values()),8192)
        for section,group in selected.items():
            for name in group:
                other=negative[name]
                self.assertNotEqual(name,other)
                self.assertEqual(f.partition_label(name),section)
                self.assertEqual(f.partition_label(other),section)
                self.assertEqual(f.fingerprint(name)[0]>>4,
                                 f.fingerprint(other)[0]>>4)
                self.assertEqual(f.features(name,name),(1,)*8)
                self.assertNotEqual(f.features(name,other),(1,)*8)
        self.assertFalse(set(selected["train"]) & set(selected["test"]))

    def test_actual_gradient_training_and_param_fingerprint(self):
        m=f.LearnedJoinComparator()
        positives=[((1,)*8,1) for _ in range(20)]
        negatives=[((0,)*8,0) for _ in range(20)]
        output=m.train(positives+negatives)
        self.assertLess(output["training_logloss_final"],
                        output["training_logloss_initial"])
        self.assertGreater(output["learned_parameter_movement_l2"],0)
        self.assertEqual(output["training_epochs"],160)
        self.assertEqual(output["learned_parameters"],9)
        self.assertEqual(output["learned_parameter_sha256"],
                         hashlib.sha256(",".join(
                            f"{v:.8f}" for v in [m.bias]+m.w).encode()).hexdigest())
        self.assertGreater(m.score((1,)*8),0.5)
        self.assertLess(m.score((0,)*8),0.5)

    def test_exact_identity_baseline_and_coarse_prefix_failure(self):
        a="some_node"
        b="some_node"
        self.assertEqual(a,b)
        self.assertEqual(f.features(a,b),(1,)*8)
        self.assertEqual(f.metrics([(a,b,1)],lambda x,y:x==y)["tp"],1)
        self.assertFalse(base.source_digest(b"this is not original source\n"))
        self.assertFalse(base.source_digest(b"question\tanswer\n"))

    def test_no_improper_graph_source_or_scientific_witness(self):
        with self.assertRaises(f.Denied):
            f.audit(b"a|role|b\n")
        with self.assertRaises(base.Denied):
            base.load_original_triples(b"a|role|b\n")
        self.assertFalse(f.STATUS.endswith("SCIENTIFIC_ACCEPTANCE"))
        self.assertEqual(f.N_TEST,256)

if __name__=="__main__":unittest.main()
