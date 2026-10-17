"""TRAIN-only F124-R frozen comparator source/weight/beam regressions."""
import copy
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import f124r_train_controls as c
import f124r_train_environment as graphs
import f124r_sparse_model as sparse

class CostAndPrune(unittest.TestCase):
    def test_equal_public_graph_inputs_and_dense_source(self):
        p,n=graphs.build(98100,[1,1,2],"Wingless")
        self.assertEqual(c.dense_work(p,c.sparse.init())["index_operations"],0)
        self.assertGreater(c.dense_work(p,c.sparse.init())["public_edge_visits"],len(p["edges"]))
        self.assertEqual(c.DENSE_B_GIT_BLOB,"6f90560c331e20967d0b13892668da8060e06cdc")
        self.assertEqual(set(c.sparse_work(p,sparse.forward(p,sparse.init(),True)[2])),
                         set(c.dense_work(p,sparse.init())))
    def test_primitive_cost_counts_hash_and_sort_not_free(self):
        p,n=graphs.build(98101,[1,1,2],"Wingless")
        s=sparse.forward(p,sparse.init(),True)[2]
        item=c.sparse_work(p,s)
        self.assertGreater(item["hashed_edge_bytes"],len(p["edges"]))
        self.assertGreater(item["sort_comparison_upper"],0)
        self.assertEqual(c.cost(item),sum(item.values()))
    def test_oracle_route_witness_is_diagnostic_not_model_input(self):
        p,n=graphs.build(98102,[1,1,2],"Wingless")
        with patch.object(graphs,"symbolic_count",side_effect=AssertionError("oracle leaked")):
            _,_,w=sparse.forward(p,sparse.init(),True)
        self.assertLessEqual(w["work"]["retained_max"],2)
        paths=c.public_exact_paths(p)
        self.assertEqual(len(paths),1)
        self.assertEqual(len(c.route_witness_hash(paths[0])),64)
    def test_train_only_split_and_score_pairing(self):
        rows=graphs.train_rows("Wingless",[[1,1,2],[3,2,0]])
        self.assertEqual(len(rows),128)
        result=c.paired(rows,lambda o: bool(graphs.symbolic_count(o)))
        self.assertEqual(result["paired_correct"],64)
        with self.assertRaises(graphs.Invalid):
            c.paired(rows[1:],lambda o:False)
    def test_unqualified_seal_fails_closed(self):
        with self.assertRaises(OSError):
            c.sealed_json("/definitely/not/a/source.json")
if __name__=="__main__":
    unittest.main()
