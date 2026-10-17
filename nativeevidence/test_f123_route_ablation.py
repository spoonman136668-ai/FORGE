"""F123 causal path sensitivity is TRAIN-only and label-blind."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import f123_route_ablation as m
import f123_multipath_environment as env

WEIGHTS=[-1.2]+[.17]*16+[.05,3.,.5]

class TrainCausalDiagnostic(unittest.TestCase):
    def graphs(self):
        return env.build(96000,[1,1,2],"Wingless","TRAIN")

    def test_trace_reconstruction_without_oracle(self):
        p,n=self.graphs()
        with patch.object(env,"symbolic_routes",side_effect=AssertionError("oracle")):
            for g in (p,n):
                t=m.b_trace(g,WEIGHTS)
                self.assertLessEqual(t["trace_error"],1e-10)
                g2=copy.deepcopy(g)
                g2["edges"].reverse()
                self.assertAlmostEqual(t["probability"],m.b_trace(g2,WEIGHTS)["probability"],places=10)
                self.assertEqual(t["winner_sha256"],m.b_trace(g2,WEIGHTS)["winner_sha256"])

    def test_onroute_and_offroute_keep_all_graph_marginals(self):
        for g in self.graphs():
            t=m.b_trace(g,WEIGHTS)
            on,off=m.interventions(g,t["path"])
            self.assertEqual(m.parity(g),m.parity(on))
            self.assertEqual(m.parity(g),m.parity(off))
            self.assertNotEqual(m.learn.digest(on),m.learn.digest(off))
            self.assertAlmostEqual(t["probability"],m.b_trace(off,WEIGHTS)["probability"],places=10)

    def test_workload_proxy_not_resource_matched(self):
        g,_=self.graphs()
        r=m.resource_proxy(g,m.b_trace(g,WEIGHTS))
        self.assertGreater(r["relative_b_to_f122_proxy"],1)
        self.assertFalse(r["resource_equivalence_proven"])
        self.assertFalse(r["wallclock_benchmark"])

    def test_privileged_fields_rejected(self):
        g,_=self.graphs()
        g["oracle_true_path"]=[0]
        with self.assertRaises(env.Invalid):
            m.b_trace(g,WEIGHTS)

    def test_no_confirmation_handling_in_analyzer(self):
        g,_=self.graphs()
        with self.assertRaises(env.Invalid):
            m.resource_proxy(g,{"hops":5,"path_count":2})

if __name__=="__main__":
    unittest.main()
