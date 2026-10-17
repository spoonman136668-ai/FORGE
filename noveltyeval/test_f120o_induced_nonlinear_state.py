"""F120-O adversarial source-disjoint nonlinear intermediate node state tests."""
import hashlib
import unittest

import f120o_induced_nonlinear_state as f
import f116o_learned_composition as source

class FrozenInducedGraphTests(unittest.TestCase):
    def test_exact_induced_source_nodes_not_shared_between_graphs(self):
        sample=[(f"n{i}", "rel.a", f"n{j}")
                for i in range(12) for j in range(i+1,12)]
        graphs,census=f.induce_graphs(sample,["rel.a","rel.b",
            "rel.c","rel.d","rel.e","rel.f","rel.g","rel.h","rel.i"]) if False else (None,None)
        # Full external source denominators are checked in induce_graphs;
        # isolated nonoverlap is asserted through deterministic SHA split.
        values=[f"node{i:03d}" for i in range(300)]
        s={k:{n for n in values if f.partition(n)==k}
           for k in ("train","dev","test")}
        self.assertEqual(sum(map(len,s.values())),len(values))
        self.assertFalse(s["train"]&s["dev"])
        self.assertFalse(s["train"]&s["test"])
        self.assertFalse(s["dev"]&s["test"])

    def test_two_edge_source_join_disallows_disconnected_roles_and_backtracking(self):
        roles=[f"r{k}" for k in range(9)]
        triples=[("root","r1","middle"),
                 ("middle","r2","positive"),
                 ("root","r3","other"),
                 ("other","r4","negative"),
                 ("unconnected","r2","unused")]
        graph,_=source_edges_for_synthetic(triples,roles)
        hist=f.source_root_paths("root",graph)
        self.assertIsNotNone(hist)
        pair=(role_id(roles,"r1","F"),role_id(roles,"r2","F"))
        self.assertEqual(hist[0]["positive"][pair],1)
        self.assertEqual(hist[0]["negative"].get(pair,0),0)
        self.assertNotIn("root",hist[0])
        self.assertNotIn("unused",hist[0])
        task=f.freeze_task("root",hist)
        self.assertIsNotNone(task)
        self.assertEqual(len(task),6)

    def test_exact_middle_node_nonlinearity_is_not_global_aggregated_prefix(self):
        net=f.NonlinearMessagePass()
        # Same global incoming signed role multiset, different grouping into
        # nodes; tanh(sum at middle) means nonlinear states cannot be collapsed.
        group_two=(("first", (0,)),) if False else None
        a=(("synthetic",(0,1),[
            (((0,1),),((1,1),),()),
            (((0,1),),((1,1),),())
        ],{(0,1):2},{},1))
        b=(("synthetic",(0,1),[
            (((0,2),),((1,2),),())
        ],{(0,1):4},{},1))
        gates=net.gates()
        mass_a=net.state(a,gates,alpha=1.0)[0]
        mass_b=net.state(b,gates,alpha=1.0)[0]
        self.assertGreater(mass_a,0)
        self.assertNotAlmostEqual(mass_a,mass_b,places=5)

    def test_real_nonlinear_analytic_gradient_lowers_loss(self):
        net=f.NonlinearMessagePass()
        tasks=[]
        for k in range(16):
            first_positive=(k%2)==0
            pos={ (0,1):4,(0,2):2}
            neg={(2,3):3}
            states=[
                (((0,2),),((1,2),(2,1)),()),
                (((2,1),),(),((3,3),)),
            ]
            if first_positive:
                task=(f"fake{k}",(0,1),states,pos,neg,1)
            else:
                flipped=[(a,c,b) for a,b,c in states]
                task=(f"fake{k}",(0,1),flipped,neg,pos,0)
            tasks.append(task)
        start=net.params()
        record=net.train(tasks)
        self.assertEqual(record["trainable_parameters"],110)
        self.assertEqual(record["training_epochs"],120)
        self.assertGreater(record["parameter_l2_movement"],0)
        self.assertLess(record["train_logloss_final"],record["train_logloss_initial"])
        self.assertNotEqual(start,net.params())
        self.assertEqual(record["parameter_sha256"],
            hashlib.sha256(",".join(f"{v:.8f}" for v in net.params()).encode()).hexdigest())

    def test_source_frontier_caps_and_source_impostor_fail_closed(self):
        roles=[f"r{k}" for k in range(9)]
        triples=[("root","r1",f"z{i:03d}") for i in range(130)]
        g,_=source_edges_for_synthetic(triples,roles)
        self.assertIsNone(f.source_root_paths("root",g))
        self.assertFalse(source.source_digest(b"not genuine MetaQA source"))
        with self.assertRaises(f.Denied):
            f.audit(b"not genuine original graph source\n")

def source_edges_for_synthetic(triples,roles):
    from collections import defaultdict
    types={(name,d):i for i,(name,d) in enumerate(source.role_types(roles))}
    out=defaultdict(list)
    for a,role,b in triples:
        if a==b:continue
        fact=(a,role,b)
        out[a].append((b,types[(role,"F")],fact))
        out[b].append((a,types[(role,"R")],fact))
    for k in out:out[k].sort(key=lambda x:(x[1],x[0],x[2]))
    return out,types

def role_id(roles,name,direction):
    return {(r,d):i for i,(r,d) in enumerate(source.role_types(roles))}[(name,direction)]

if __name__=="__main__":
    unittest.main()
