"""ACC35 prereg/source-only batch worker audit, no actual source environment."""
import json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
SOURCE=ROOT/"research/acceleration/acc34_go_delta"
PREREG=(ROOT/"docs/research/ACC-35-BATCHED-VERIFIED-CPU-PREREG.md").read_text(encoding="utf-8")
WORKER=(SOURCE/"cmd/batchworker/main.go").read_text(encoding="utf-8")
DRIVER=(SOURCE/"cmd/batchdriver/main.go").read_text(encoding="utf-8")
INDEX=json.loads((ROOT/"research/acceleration/acc34_portfolio_index.json").read_text(encoding="utf-8"))
class Acc35FrozenBatchedResource(unittest.TestCase):
    def test_new_prereg_separate_from_old_single_worker_negative(self):
        for x in ("ACC-34","ACC-35","1.099078","1.102968",
                  "32 independently reset","131,072","0.90","1.10",
                  "91101, 91103, 91107, 91109, 91111"):
            self.assertIn(x,PREREG)
    def test_computation_kernel_identity_and_worker_batch(self):
        self.assertIn("const Batch=32",WORKER)
        self.assertIn("a.Run(*mode,*scenario,*seed+k,*events)",WORKER)
        self.assertIn('row.FitEvaluations+=r.FitEvaluations',WORKER)
        self.assertIn('row.VerificationEvaluations+=r.VerificationEvaluations',WORKER)
        self.assertIn('SessionChecksums []string',WORKER)
        self.assertIn('RuntimeTotalAllocBytes',WORKER)
    def test_process_cpu_and_all_session_fidelity_without_unsound_shortcut(self):
        self.assertIn("cmd.ProcessState.UserTime().Nanoseconds()+cmd.ProcessState.SystemTime().Nanoseconds()",DRIVER)
        self.assertIn("len(v.Worker.SessionChecksums)!=32",DRIVER)
        self.assertIn("v.Worker.SessionChecksums[k]!=f.Worker.SessionChecksums[k]",DRIVER)
        self.assertIn("ACC35_MISSING_CHILD_PROCESS_CPU_OR_WALL",DRIVER)
        self.assertIn("ACC35_NO_TOTAL_VERIFIED_BULK_GO_CPU_WIN__NO_SCIENCE",DRIVER)
        self.assertIn("len(result.Samples)!=40",DRIVER)
    def test_all_thirty_six_unpromoted_models_and_existing_source_preserved(self):
        self.assertEqual(len(INDEX["rows"]),36)
        self.assertEqual(len({r["claim_id"] for r in INDEX["rows"]}),36)
        self.assertTrue(all(not r["native_model_acceleration_proven"] for r in INDEX["rows"]))
        self.assertFalse(INDEX["scientific_admission"])
        self.assertFalse(INDEX["protected_main_or_controller_modified"])
if __name__=="__main__":unittest.main()
