"""O11 train-only source, trace custody and reconciliation regression tests."""
import copy
import math
import unittest

from public_source import (
    FAMILIES,ROLES,COUNT,QUERY_TIMES,UnauthorizedSource,seed,
    public_episode,public_train,digest,query_info,
)
from o10_immutable_phase import PublicPhaseComposer
from train_only_trace import (
    TRACE,MODELS,SEEDS,guard,native_math_probes,snapshot,trace_run,
)
from compare import compare


class O11TrainForensicsTests(unittest.TestCase):
    def test_protocol_precedes_model_probe_and_roles(self):
        p=guard()
        self.assertEqual(p["stage"] if "stage" in p else
                         p["frozen_stage"],
                         "BEFORE_ANY_PROBE_SOURCE_AND_EXECUTION")
        self.assertEqual(p["role_namespace"],"o11-determinism-training-probe-v1")
        self.assertEqual(p["training"]["trace_after_updates"],list(TRACE))

    def test_new_train_only_role_and_no_o10_or_protected_data(self):
        for role in ("O10_TRAIN","O10_SELECT","O10_DEV","O11_DEV",
                     "HELD","ORIGINAL","Q21_FIT","FIT_TRAIN"):
            with self.assertRaises(UnauthorizedSource):
                public_episode(role,FAMILIES[0],0)
        for i in (-1,96,True,1.0,"0"):
            with self.assertRaises(UnauthorizedSource):
                seed(ROLES[0],FAMILIES[0],i)

    def test_all_new_training_episodes_valid_and_disjoint_family_hashes(self):
        hashes=[]
        for family in FAMILIES:
            batch=public_train(family)
            self.assertEqual(len(batch),COUNT)
            self.assertTrue(all(query_info(ep)["query_t"] in QUERY_TIMES
                                for ep in batch))
            for ep in batch:
                self.assertTrue(all(ep[t][2]==ep[t+1][0]
                                    for t in range(23)))
            hashes.append(digest(batch))
        self.assertEqual(len(set(hashes)),4)

    def test_identical_train_only_source_reproducibility(self):
        for family in FAMILIES:
            self.assertEqual(
                public_episode(ROLES[0],family,0),
                public_episode(ROLES[0],family,0))

    def test_original_phase_source_has_actual_training_gradient(self):
        ep=public_train(FAMILIES[0])[0]
        model=PublicPhaseComposer("TRAINED_PHASE_MEMORY",17)
        before=model.checkpoint()
        loss,grad=model.loss_gradient(ep)
        self.assertTrue(math.isfinite(loss))
        self.assertEqual(len(grad),8)
        self.assertEqual(before,model.checkpoint())
        model.step(ep)
        self.assertNotEqual(before,model.checkpoint())

    def test_trace_only_contains_predeclared_steps_and_train_inputs(self):
        batch=public_train(FAMILIES[0])
        z=trace_run(FAMILIES[0],"TRAINED_PHASE_MEMORY",17,batch)
        self.assertEqual(tuple(x["step"] for x in z["trace"]),TRACE)
        self.assertEqual(z["n_training_updates"],3840)
        for entry in z["trace"]:
            self.assertEqual(len(entry["weight_hex"]),8)
            self.assertEqual(len(entry["moment1_hex"]),8)
            self.assertEqual(len(entry["train_probe_gradient_hex"]),8)
            self.assertTrue(all(math.isfinite(float.fromhex(x))
                                for x in entry["weight_hex"]))

    def test_math_probe_public_inputs_are_finite(self):
        z=native_math_probes()
        self.assertGreaterEqual(len(z),9)
        self.assertTrue(all(math.isfinite(float.fromhex(v))
                            for ops in z.values() for v in ops.values()))

    def _synthetic_receipt(self):
        empty="0x0.0p+0"
        trace=[{"step":s,
                "weight_hex":[empty]*8,
                "moment1_hex":[empty]*8,
                "moment2_hex":[empty]*8,
                "train_probe_gradient_hex":[empty]*8,
                "train_probe_loss_hex":empty,
                "phase_hex":empty,
                "sin_phase_hex":empty,
                "cos_phase_hex":empty}
               for s in TRACE]
        return {
            "schema":"forge.optimizer.o11.native-train-only-trace.v1",
            "code_identity":"O10_PHASE_BLOB_56203c6aa60b29c4a5e8fb4bcd250bc212582209",
            "O10_TRAIN_SELECT_DEV_CONSUMED":0,
            "PROTECTED_FIRST_USE":False,
            "o11_new_source_sha256":{f:"a"*64 for f in FAMILIES},
            "math_library_probes":{"0.1":{"sin_hex":"0x0.0p+0",
                                               "cos_hex":"0x1.0p+0",
                                               "exp_hex":"0x1.0p+0"}},
            "traces":[{"family":f,"variant":k,"seed":s,
                       "last_checkpoint_sha256":"b"*64,
                       "trace":copy.deepcopy(trace)}
                      for f in FAMILIES for k in MODELS for s in SEEDS],
        }

    def test_native_reconcile_reports_zero_divergence_without_claiming_science(self):
        a=self._synthetic_receipt()
        z=compare(a,copy.deepcopy(a))
        self.assertEqual(z["independent_models_checked"],24)
        self.assertIsNone(z["earliest_exact_model_drift_step"])
        self.assertFalse(z["scientific_GO"])

    def test_native_reconcile_detects_early_adam_weight_drift(self):
        a=self._synthetic_receipt()
        b=copy.deepcopy(a)
        first=b["traces"][0]["trace"][2]
        first["weight_hex"][1]=(1e-3).hex()
        z=compare(a,b)
        p=z["models"][0]
        self.assertEqual(p["first_exact_native_float_mismatch_step"],2)
        self.assertEqual(p["first_weight_divergence_gt_1e-6_step"],2)
        self.assertGreater(p["maximum_weight_absolute_difference"],1e-6)

    def test_native_reconcile_refuses_mismatched_training_hashes(self):
        a=self._synthetic_receipt()
        b=copy.deepcopy(a)
        b["o11_new_source_sha256"][FAMILIES[0]]="0"*64
        with self.assertRaisesRegex(ValueError,"SOURCE_SHA_DRIFT"):
            compare(a,b)

    def test_missing_or_duplicate_trace_coverage_fails_closed(self):
        a=self._synthetic_receipt()
        b=copy.deepcopy(a)
        b["traces"][0]["trace"].pop()
        with self.assertRaisesRegex(ValueError,"TRACE"):
            compare(a,b)


if __name__=="__main__":
    unittest.main()
