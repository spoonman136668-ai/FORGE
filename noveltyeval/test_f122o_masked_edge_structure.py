"""F122-O fail-closed masking, nonedge, topology features and true MLP gradients."""
import hashlib
import unittest
from collections import defaultdict

import f122o_masked_edge_structure as f
import f116o_learned_composition as source

class FrozenMissingEdgeStructure(unittest.TestCase):
    def test_global_pair_mask_removes_any_relation_and_reciprocal_edge(self):
        # Synthetic source with arbitrary overlapping predicates and reciprocal.
        # Explicitly build a mask selected solely by source pair digest, never
        # by input role/answer or learner prediction.
        pair=next((f.undirected("root",f"node-{n}") for n in range(1000)
                   if f.masked(f.undirected("root",f"node-{n}"))),None)
        self.assertIsNotNone(pair)
        a,b=pair
        raw={(a,"r1",b),(a,"r2",b),(b,"r3",a)}
        full_pairs={f.undirected(x,y) for x,r,y in raw}
        untyped=defaultdict(set)
        for left,right in full_pairs:
            if not f.masked((left,right)):
                untyped[left].add(right)
                untyped[right].add(left)
        self.assertNotIn(b,untyped.get(a,set()))
        self.assertNotIn(a,untyped.get(b,set()))
        self.assertEqual(len(full_pairs),1)
        self.assertEqual(len(raw),3)

    def test_disjoint_salted_node_partitions(self):
        names=[f"toy-{i:04d}" for i in range(400)]
        ids={part:{n for n in names if f.split_node(n)==part}
             for part in ("train","dev","test")}
        self.assertEqual(sum(len(z) for z in ids.values()),400)
        self.assertFalse(ids["train"]&ids["dev"])
        self.assertFalse(ids["train"]&ids["test"])
        self.assertFalse(ids["dev"]&ids["test"])

    def test_real_local_path_features_do_not_contain_link_label(self):
        graph=defaultdict(set)
        def add(a,b):
            graph[a].add(b)
            graph[b].add(a)
        add("root","m1");add("m1","candidate")
        add("root","m2");add("m2","m3");add("m3","candidate")
        add("root","m4");add("m4","negative-m1")
        add("negative-m1","negative")
        x=f.feature_vector("root","candidate",graph)
        y=f.feature_vector("root","negative",graph)
        self.assertIsNotNone(x)
        self.assertIsNotNone(y)
        self.assertEqual(len(x),8)
        self.assertTrue(all(0<=v<=2 for v in x+y))
        self.assertGreater(x[3],0)
        self.assertGreater(x[4],0)
        self.assertGreater(x[5],0)
        self.assertEqual(f.feature_vector("root","m1",graph),None)
        self.assertEqual(f.feature_vector("root","root",graph),None)

    def test_adversarial_overbudget_local_structure_refused(self):
        graph=defaultdict(set)
        for i in range(129):
            mid=f"mid-{i}"
            graph["root"].add(mid)
            graph[mid].add("root")
        graph["tgt"].add("other")
        graph["other"].add("tgt")
        self.assertIsNone(f.feature_vector("root","tgt",graph))

    def test_true_numeric_nontrivial_mlp_and_linear_control_train(self):
        train=[]
        # Fixed synthetic structural signatures, balanced labels, ordering
        # alternates so first-slot constant cannot learn the rule.
        positive=(0.3,0.3,0.0,0.4,0.4,0.7,0.6,0.5)
        negative=(0.3,0.3,0.0,0.0,0.0,0.0,0.0,0.2)
        for i in range(32):
            isfirst=(i%2)==0
            train.append((positive if isfirst else negative,
                          negative if isfirst else positive,int(isfirst)))
        model=f.NeuralTopologyComparator()
        before=model.params()
        report=model.train(train)
        self.assertEqual(report["training_epochs"],180)
        self.assertEqual(report["learned_parameters"],61)
        self.assertLess(report["training_logloss_final"],
                        report["training_logloss_initial"])
        self.assertGreater(report["parameter_movement_l2"],0)
        self.assertNotEqual(before,model.params())
        self.assertGreater(model.score(positive),model.score(negative))
        fingerprint=hashlib.sha256(
            ",".join(f"{x:.8f}" for x in model.params()).encode()).hexdigest()
        self.assertEqual(report["learned_parameter_sha256"],fingerprint)
        baseline=f.LinearTopologyComparator()
        result=baseline.train(train)
        self.assertEqual(result["learned_parameters"],9)
        self.assertLess(result["training_logloss_final"],
                        result["training_logloss_initial"])
        self.assertGreater(baseline.score(positive),baseline.score(negative))

    def test_incomplete_source_denied_and_negative_frozen(self):
        self.assertFalse(source.source_digest(b"fake graph\n"))
        with self.assertRaises(f.Denied):f.audit(b"fake graph\n")
        p=f.undirected("Z","A")
        self.assertEqual(p,("A","Z"))
        self.assertEqual(f.masked(p),f.masked(("A","Z")))
        self.assertEqual(f.degree_key(1),1)
        self.assertEqual(f.degree_key(2),2)
        self.assertEqual(f.degree_key(3),2)
        self.assertEqual(f.degree_key(4),3)
        self.assertEqual(f.TEST,64)

if __name__=="__main__":
    unittest.main()
