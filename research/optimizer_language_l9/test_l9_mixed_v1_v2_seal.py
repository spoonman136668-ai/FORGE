"""Pure-source L9 V1-GRU/V2-Transformer numerical custodian and negative tests."""
import copy
import hashlib
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import l9_mixed_v1_v2_seal as m
import test_l9_seal_select as original_tests


class MixedSelectSealTests(unittest.TestCase):
    def candidate(self):
        return original_tests.SealSelectTests().candidate()

    def original_gru(self,seed):
        d=original_tests.SealSelectTests().case("GRU_SEQ2SEQ",seed)
        d["fit_receipt_sha256"]=m.EXPECTED_FIT[("GRU_SEQ2SEQ",seed)]
        for row in d["all_epoch_metrics"]:
            row["checkpoint_sha256"]=m.FROZEN_CHECKPOINTS[("GRU_SEQ2SEQ",seed)][row["epoch"]]
        d["selected_checkpoint_sha256"]=m.FROZEN_CHECKPOINTS[
            ("GRU_SEQ2SEQ",seed)][d["selected_epoch"]]
        return d

    def transformer(self,seed):
        epochs=[]
        for i,epoch in enumerate((4,8,12)):
            coverage=0
            epochs.append({
                "arm":"SMALL_TRANSFORMER","seed":seed,"epoch":epoch,
                "checkpoint_sha256":m.FROZEN_CHECKPOINTS[("SMALL_TRANSFORMER",seed)][epoch],
                "retained_model_bytes":1721741,"role":"L9_SELECT",
                "records":2154,"triple_denominator":6135,
                "triple_proxy_hits":0,"missing_triples_proxy":6135,
                "requested_content_proxy_coverage":coverage,
                "chrf_single_reference_proxy":(0,0.011066673,0.055673619)[i],
                "explicit_abstentions":(2154,1995,1572)[i],
                "reference_bytes_evaluated":242996,
                "evaluation_cpu_seconds":20+i,"evaluation_wall_seconds":10+i})
        return {"schema":m.V2_SCHEMA,"status":m.V2_STATUS,
            "arm":"SMALL_TRANSFORMER","seed":seed,
            "source_role_sha256":m.ROLE_SHA,"model_suite_git_blob":m.SUITE_BLOB,
            "train_count":8480,"select_count":2154,
            "cross_os_synthetic_prefit_run":m.V2_PREFIT,
            "selected_metric_is_nonadjudicated_proxy":True,
            "not_interchangeable_with_frozen_v1_receipt":True,
            "new_independent_seal_and_acceptance_required":True,
            "audit_dev_reference_consumed":False,
            "official_test_consumed":False,"scientific_go":False,
            "flops":"NOT_MEASURED","energy":"NOT_MEASURED",
            "fit_receipt_sha256":m.EXPECTED_FIT[("SMALL_TRANSFORMER",seed)],
            "original_failure_run_id":m.ORIGINAL_TIMEOUTS[seed]["run"],
            "original_failure_job_id":m.ORIGINAL_TIMEOUTS[seed]["job"],
            "original_failure_receipt_sha256":"a"*64,
            "original_workflow_receipt_sha256":"b"*64,
            "original_timeout_log_sha256":"c"*64,
            "synthetic_prefit_receipt_sha256":"d"*64,
            "python_peak_traced_bytes":12345,
            "all_epoch_metrics":epochs,
            "development_equivalence_fixtures":[
                {"epoch":e,"index":idx,"identical":True}
                for e in (4,8,12) for idx in m.PAIR_INDEXES],
            "selected_epoch":12,"selected_checkpoint_sha256":
                m.FROZEN_CHECKPOINTS[("SMALL_TRANSFORMER",seed)][12]}

    def test_real_source_identity_and_pending_gate(self):
        self.assertIsNone(m.V2_RECEIPTS[1701])
        self.assertEqual(m.legacy.SELECT_SCHEMA,
            "forge.optimizer.language.l9.neural-select-development-v1")
        self.assertNotEqual(m.SCHEMA,m.legacy.SCHEMA)
        self.assertNotEqual(m.V2_SCHEMA,m.legacy.SELECT_SCHEMA)
        self.assertEqual(m.ROLE_SHA,m.legacy.ROLE_SHA)
        self.assertEqual(set(m.FROZEN_CHECKPOINTS),set(m.EXPECTED_FIT))
        for epochs in m.FROZEN_CHECKPOINTS.values():
            self.assertEqual(set(epochs),{4,8,12})
            for sha in epochs.values():
                self.assertEqual(len(sha),64)

    def test_v2_numerical_receipt_exact_grid(self):
        for seed in (1701,1702):
            v=m.check_v2(self.transformer(seed),seed)
            self.assertEqual(v["selected_epoch"],12)
            self.assertEqual(v["requested_content_proxy_coverage"],0)
            self.assertEqual(v["explicit_abstentions"],1572)
            self.assertEqual(v["receipt_type"],
                "SEPARATELY_QUALIFIED_RECOVERY_V2_NOT_V1")
            self.assertEqual(v["original_v1_select_outcome"],
                "CANCELLED_90M_NO_RECEIPT")

    def test_v2_tampering_fail_closed(self):
        cases=[
            lambda d:d.update({"schema":m.legacy.SELECT_SCHEMA}),
            lambda d:d.update({"status":"SELECT_ONLY_DEVELOPMENT_CHECKPOINT_CHOICE"}),
            lambda d:d.update({"scientific_go":True}),
            lambda d:d.update({"audit_dev_reference_consumed":True}),
            lambda d:d.update({"official_test_consumed":True}),
            lambda d:d.update({"original_failure_job_id":-1}),
            lambda d:d.update({"cross_os_synthetic_prefit_run":-1}),
            lambda d:d.update({"fit_receipt_sha256":"f"*64}),
            lambda d:d.update({"not_interchangeable_with_frozen_v1_receipt":False}),
            lambda d:d.update({"selected_epoch":4}),
            lambda d:d["all_epoch_metrics"].pop(),
            lambda d:d["all_epoch_metrics"][1].update({"epoch":4}),
            lambda d:d["all_epoch_metrics"][0].update({"checkpoint_sha256":"f"*64}),
            lambda d:d["all_epoch_metrics"][0].update({"triple_proxy_hits":10}),
            lambda d:d["all_epoch_metrics"][0].update({"triple_denominator":1}),
            lambda d:d["all_epoch_metrics"][0].update({"requested_content_proxy_coverage":.3}),
            lambda d:d["all_epoch_metrics"][0].update({"chrf_single_reference_proxy":float("nan")}),
            lambda d:d["all_epoch_metrics"][0].update({"explicit_abstentions":2155}),
            lambda d:d["all_epoch_metrics"][0].update({"evaluation_wall_seconds":float("inf")}),
            lambda d:d["all_epoch_metrics"][0].update({"role":"L9_AUDIT_DEV"}),
            lambda d:d["development_equivalence_fixtures"].pop(),
            lambda d:d["development_equivalence_fixtures"][0].update({"identical":False}),
            lambda d:d["development_equivalence_fixtures"][1].update({"index":0}),
        ]
        for seed in (1701,1702):
            for i,mutation in enumerate(cases):
                d=self.transformer(seed)
                mutation(d)
                with self.subTest(seed=seed,negative=i),self.assertRaises(ValueError):
                    m.check_v2(d,seed)

    def test_no_v2_1701_artifact_blocks_seal_even_with_other_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/"seal.json"
            with self.assertRaisesRegex(ValueError,"PENDING_AUTHENTICATED_V2_SEED_1701"):
                m.mixed_seal(root/"missing-candidate",root/"missing",out)
            self.assertFalse(out.exists())

    def test_exact_four_case_synthetic_fixture_can_pass_only_when_pinned(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);neural=root/"neural";neural.mkdir()
            candidate=root/"candidate.json"
            candidate.write_bytes(m.legacy.canonical_bytes(self.candidate()))
            approved={}
            for seed in (1701,1702):
                for arm,case in (("GRU_SEQ2SEQ",self.original_gru(seed)),
                                 ("SMALL_TRANSFORMER",self.transformer(seed))):
                    raw=m.legacy.canonical_bytes(case)
                    (neural/f"{arm}-{seed}.json").write_bytes(raw)
                    approved[(arm,seed)]=m.sha(raw)
            with patch.object(m.legacy,"CANDIDATE_RECEIPT_SHA",m.sha(candidate.read_bytes())):
                with patch.dict(m.GRU_RECEIPTS,{
                      1701:approved[("GRU_SEQ2SEQ",1701)],
                      1702:approved[("GRU_SEQ2SEQ",1702)]}):
                    with patch.dict(m.V2_RECEIPTS,{
                      1701:approved[("SMALL_TRANSFORMER",1701)],
                      1702:approved[("SMALL_TRANSFORMER",1702)]}):
                        out=root/"sealed.json"
                        result=m.mixed_seal(candidate,neural,out)
                        self.assertEqual(len(result["neural_checkpoint_selection"]),4)
                        self.assertEqual(result["neural_checkpoint_selection"][0]["receipt_type"],
                                         "ORIGINAL_FROZEN_V1")
                        self.assertEqual(result["neural_checkpoint_selection"][2]["receipt_type"],
                                         "SEPARATELY_QUALIFIED_RECOVERY_V2_NOT_V1")
                        self.assertFalse(result["original_v1_select_seal_complete"])
                        self.assertFalse(result["audit_dev_references_consumed"])
                        self.assertFalse(result["scientific_go"])
                        self.assertEqual(m.sha(out.read_bytes()),m.sha(
                            m.legacy.canonical_bytes(result)))
                        with self.assertRaisesRegex(ValueError,"NO_OVERWRITE"):
                            m.mixed_seal(candidate,neural,out)

    def test_missing_and_wrong_receipt_never_emits_seal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);neural=root/"neural";neural.mkdir()
            candidate=root/"candidate.json"
            candidate.write_bytes(m.legacy.canonical_bytes(self.candidate()))
            with patch.dict(m.V2_RECEIPTS,{1701:"f"*64}):
                with patch.object(m.legacy,"CANDIDATE_RECEIPT_SHA",
                                  m.sha(candidate.read_bytes())):
                    with self.assertRaises(FileNotFoundError):
                        m.mixed_seal(candidate,neural,root/"out.json")
            self.assertFalse((root/"out.json").exists())

    def test_no_corpus_or_model_read_sources(self):
        s=(Path(__file__).resolve().parent/"l9_mixed_v1_v2_seal.py").read_text()
        for forbidden in ("load_train_select(", "train_neural(",
                          "load_audit(", "torch.load(", "import torch",
                          "requests.", "subprocess.", "webnlg-dataset"):
            self.assertNotIn(forbidden,s)


if __name__=="__main__":
    unittest.main()
