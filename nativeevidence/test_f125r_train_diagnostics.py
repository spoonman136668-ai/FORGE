"""F125-R original-weight, label-blind TRAIN-only diagnostic guards."""
import copy
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import f125r_train_diagnostics as diag
import f125r_train_environment as env
import f125r_path_model as model

class CausalDiagnostics(unittest.TestCase):
    def test_null_wrong_role_swap_keeps_input_marginals(self):
        for label, graph in zip((1,0),env.build(100100,[1,2,3],"Wingless")):
            null=diag.wrong_role_null(graph)
            self.assertEqual(env.marginals(graph),env.marginals(null))
            a=model.forward(graph,list(model.INIT))[0]
            b=model.forward(null,list(model.INIT))[0]
            self.assertAlmostEqual(a,b,places=10)
            self.assertEqual(env.graph_paths(null,True),label)
    def test_duplicate_wrong_role_tokens_still_use_distinct_null(self):
        _,negative=env.build(100100,[1,2,3],"Wingless")
        roles=set(negative["roles"])
        candidates=sorted(((i,e) for i,e in enumerate(negative["edges"])
                           if e["role"] not in roles),
                          key=lambda pair:(pair[1]["from"],pair[1]["to"],
                                           pair[1]["role"],model.edge_id(pair[1])))
        self.assertGreaterEqual(len(candidates),3)
        negative["edges"][candidates[1][0]]["src_bits"]=list(
            negative["edges"][candidates[0][0]]["src_bits"])
        original=env.marginals(negative)
        null=diag.wrong_role_null(negative)
        self.assertNotEqual(null,negative)
        self.assertEqual(env.marginals(null),original)
        self.assertAlmostEqual(model.forward(null,model.INIT)[0],
                               model.forward(negative,model.INIT)[0],places=10)
    def test_no_ground_truth_in_model_read(self):
        p,_=env.build(100101,[1,2,3],"Wingless")
        with patch.object(env,"graph_paths",
                          side_effect=AssertionError("oracle leakage")):
            model.forward(p,list(model.INIT))
            diag.wrong_role_null(p)
    def test_no_stale_or_unauthenticated_train_diagnostic(self):
        with self.assertRaises(env.Invalid):
            diag.diagnose({}, {}, {"schema":"forged"},"0"*40)
    def test_model_threshold_and_cohort_untouched(self):
        self.assertEqual(model.EPOCHS,100)
        self.assertEqual(model.PARAMS,20)
        self.assertEqual(diag.SCHEMA,
           "forge.autonomy.f125r.train-only-calibration-causal-diagnostic.v1")
        self.assertFalse(hasattr(diag,"fit"))
        for lane,seed in (("Wingless",100200),("Yggdrasil",101200)):
            with self.assertRaises(env.Invalid):
                env.build(seed,[1,2,3],lane)

if __name__=="__main__":
    unittest.main()
