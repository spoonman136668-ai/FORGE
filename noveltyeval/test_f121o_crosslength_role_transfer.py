"""F121-O role-alignment inductive prior + source-real three-hop negative controls."""
import hashlib
import unittest

import f121o_crosslength_role_transfer as f
import f116o_learned_composition as original

def synthetic_arcs(triples,roles):
    from collections import defaultdict
    ids={(r,d):i for i,(r,d) in enumerate(original.role_types(roles))}
    graph=defaultdict(list)
    for a,r,b in triples:
        if a==b:continue
        fact=(a,r,b)
        graph[a].append((b,ids[(r,"F")],fact))
        graph[b].append((a,ids[(r,"R")],fact))
    for node in graph:
        graph[node].sort(key=lambda v:(v[1],v[0],v[2]))
    return graph,ids

class CrossLengthFrozenExperiment(unittest.TestCase):
    def test_salted_source_partition_node_disjoint(self):
        nodes=[f"fake-source-node-{i:04d}" for i in range(300)]
        split={s:{n for n in nodes if f.subgraph_partition(n)==s}
               for s in ("train","dev","test")}
        self.assertEqual(sum(len(group) for group in split.values()),300)
        self.assertFalse(split["train"]&split["test"])
        self.assertFalse(split["dev"]&split["test"])
        self.assertFalse(split["train"]&split["dev"])

    def test_exact_three_hop_shared_middle_provenance_not_pairwise_existential(self):
        triples=[("root","r1","m1"),("m1","r2","m2"),
                 ("m2","r3","target"),("root","r4","x"),
                 ("x","r5","y"),("y","r6","negative"),
                 ("outside","r2","other")]
        roles=[f"r{i}" for i in range(9)]
        graph,ids=synthetic_arcs(triples,roles)
        hist=f.three_hop_histogram("root",graph)
        query=(ids[("r1","F")],ids[("r2","F")],ids[("r3","F")])
        self.assertEqual(hist["target"][query],1)
        self.assertEqual(hist["negative"].get(query,0),0)
        self.assertNotIn("root",hist)
        self.assertNotIn("other",hist)
        t=f.choose_task("root",hist)
        self.assertIsNotNone(t)
        self.assertEqual(len(t[1]),3)

    def test_reverse_immediate_physical_edge_same_triple_not_counted(self):
        triples=[("a","r1","b"),("b","r2","c")]
        roles=[f"r{i}" for i in range(9)]
        graph,_=synthetic_arcs(triples,roles)
        hist=f.three_hop_histogram("a",graph)
        self.assertEqual(hist,{})
        self.assertIsNone(f.choose_task("a",hist))

    def test_three_hop_strict_budget_no_truncation(self):
        triples=[("root","r1",f"n{i:03d}") for i in range(130)]
        graph,_=synthetic_arcs(triples,[f"r{i}" for i in range(9)])
        self.assertIsNone(f.three_hop_histogram("root",graph))

    def test_true_trainable_eta_updates_and_decreases_loss(self):
        model=f.AlignedRoleGate()
        train=[]
        for k in range(16):
            pos={(0,0):5,(1,2):1}
            neg={(3,4):4,(5,6):1}
            is_first=(k%2)==0
            train.append((f"fake-root-{k}",(0,0),
                         pos if is_first else neg,
                         neg if is_first else pos,
                         int(is_first)))
        initial=model.params()
        record=model.train(train)
        self.assertEqual(record["trainable_parameters"],110)
        self.assertEqual(record["training_epochs"],120)
        self.assertLess(record["training_loss_final"],
                        record["training_loss_initial"])
        self.assertGreater(record["parameter_movement_l2"],0)
        self.assertNotEqual(initial,model.params())
        self.assertGreater(model.eta,0.0)
        data=",".join(f"{z:.8f}" for z in model.params()).encode()
        self.assertEqual(record["parameter_vector_sha256"],
                         hashlib.sha256(data).hexdigest())
        self.assertGreater(model.gates()[0][0],model.gates()[0][4])

    def test_only_two_hop_labels_admitted_to_training(self):
        m=f.AlignedRoleGate()
        with self.assertRaises(f.Denied):
            m.train([("fake",(0,1,2),{(0,1,2):1},{(4,5,6):1},1)])
        self.assertFalse(original.source_digest(b"Q\tA\n"))
        with self.assertRaises(f.Denied):
            f.audit(b"not original immutable graph\n")
        self.assertEqual(f.TEST,32)

if __name__=="__main__":
    unittest.main()
